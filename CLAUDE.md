# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sentinel Pro** is a production-grade, context-aware fraud detection platform. It combines a deterministic rules engine with an XGBoost ML model, cost-aware thresholding, and async LLM explanations. The system has two distinct layers:

- **Root project** (`backend/`, `frontend/`) — a simpler, single-process FastAPI + Streamlit app that directly loads the MLflow `fraud_model/` artifact.
- **Sentinel service** (`sentinel/`) — a production-ready, multi-service implementation with PostgreSQL, Redis, Celery workers, WebSockets, Prometheus metrics, and full MLOps tooling.

## Commands

All production commands are run from `sentinel/`:

```bash
# Full stack (Docker Compose — PostgreSQL, Redis, Celery, Prometheus, Grafana)
cd sentinel
make dev          # build + start foreground
make dev-bg       # build + start background
make down         # stop all services

# ML model
make train        # train XGBoost on PaySim CSV (data/ must exist)
make tune         # Optuna HPO (50 trials)

# Tests
make test         # full suite with coverage (80% required)
make test-unit    # unit tests only (no HTTP)
make test-int     # integration tests only (full stack)

# Code quality
make lint         # Ruff check
make format       # Ruff format
make typecheck    # Mypy strict mode

# Debugging
make logs         # tail backend + celery_worker logs
make clean        # remove __pycache__ and .pytest_cache
```

Manual backend startup (without Docker):

```bash
cd sentinel
pip install -e ".[dev]"
docker-compose up -d postgres redis   # still needs these
uvicorn sentinel.src.api.main:app --reload --port 8000
streamlit run frontend/app.py
```

Root-level app (minimal, no Docker):

```bash
uvicorn backend.main:app --reload --port 8000
streamlit run frontend/app.py
```

`backend/main.py` auto-rebuilds the `fraud_model/` artifact on startup when it's missing (synthetic PaySim-shaped data, see `_rebuild_model` in `backend/main.py`). To regenerate it manually run `python rebuild_model.py` from the repo root. There is no `export_model.py` script — MLflow artifact export happens inside `sentinel/ml/train.py`.

Render / single-container deploy uses the root `Dockerfile` (Python 3.10, copies `sentinel/` into `/app/`, installs `frontend/requirements.txt`, runs `python frontend/app.py`).

## Architecture

### Request Flow

```
POST /v1/predict
  → Auth (JWT or x-api-key)
  → Redis INCR velocity (O(1), 1-hour TTL)
  → DetectionService (sentinel/src/services/detection.py):
      1. Rules engine — Phantom Drain, Magic Money, Large Value
      2. Feature engineering (sentinel/ml/features.py) — 8 features
      3. XGBoost predict_proba → confidence score
      4. Cost-aware threshold: t* = FP_cost / (FP_cost + FN_cost)
      5. Decision fusion (rules + ML + velocity) → ALLOW / CHALLENGE / BLOCK
  → Persist to PostgreSQL
  → WebSocket broadcast (if BLOCK)
  → Queue Celery tasks (SHAP + LLM — non-blocking, response returned first)
  → Return PredictionResponse (<100ms)
```

### Key Architectural Decisions

1. **Rules before ML** — deterministic hard rules fire before XGBoost to catch known patterns without model inference cost.
2. **Cost-aware threshold** — Bayes-optimal `t* = FP_cost / (FP_cost + FN_cost)` (default: `$5 / ($5 + $850) ≈ 0.006`, clamped to `[0.1, 0.9]`). Tune via `FRAUD_FP_COST` / `FRAUD_FN_COST` env vars.
3. **SHAP over LIME** — exact TreeExplainer for tree models; runs async via Celery after response is sent.
4. **LLM as post-hoc explainer only** — Llama 3 narrative never influences prediction; failure is silent.
5. **PSI for drift** — custom Population Stability Index (not Evidently); threshold at 0.2 triggers Celery retrain task.

### Directory Map

```
ai-fraud-intelligent-system/
├── backend/
│   ├── main.py            # Root FastAPI app (simple, single-process)
│   └── database.py        # SQLite-backed transaction log + velocity
├── frontend/
│   └── app.py             # Streamlit UI for root app
├── fraud_model/           # Exported MLflow artifact (binary — not in git)
│   ├── MLmodel
│   └── model.xgb
└── sentinel/              # Production service
    ├── src/
    │   ├── api/
    │   │   ├── main.py            # FastAPI app factory with lifespan
    │   │   ├── deps.py            # DB/Redis/auth dependency injection
    │   │   ├── middleware.py      # Request ID + Prometheus instrumentation
    │   │   └── routes/
    │   │       ├── predict.py     # POST /v1/predict, /v1/predict/batch
    │   │       ├── explain.py     # GET /v1/explain/{txn_id}
    │   │       ├── health.py      # GET /v1/health, /v1/drift, /v1/metrics
    │   │       ├── history.py     # GET /v1/history
    │   │       └── websocket.py   # WS /ws/alerts
    │   ├── services/
    │   │   ├── detection.py       # Orchestrates rules → ML → threshold → decision
    │   │   ├── velocity.py        # Redis sliding-window counter
    │   │   ├── drift.py           # PSI computation
    │   │   ├── explainer.py       # Dispatches async SHAP + LLM tasks
    │   │   └── websocket_manager.py
    │   ├── core/
    │   │   ├── config.py          # pydantic-settings (all typed env vars)
    │   │   ├── database.py        # Async SQLAlchemy + Transaction ORM model
    │   │   ├── redis_client.py    # Async Redis connection pool
    │   │   └── security.py        # JWT + API key auth
    │   └── schemas/               # Pydantic request/response models
    ├── ml/
    │   ├── features.py            # Feature engineering (shared by train + infer)
    │   ├── loader.py              # ModelRegistry singleton (champion + challenger)
    │   ├── ab_test.py             # Deterministic MD5-hash A/B routing
    │   ├── train.py               # PaySim training pipeline + MLflow tracking
    │   ├── evaluate.py            # PR-AUC, calibration, cost curves
    │   └── tune.py                # Optuna HPO (50 trials)
    ├── workers/
    │   ├── celery_app.py          # Celery config (Redis broker + JSON serializer)
    │   └── tasks/
    │       ├── shap_task.py       # Async SHAP TreeExplainer → top 5 features
    │       ├── llm_task.py        # Async Llama 3-8B narrative (max 60 tokens)
    │       ├── batch_task.py      # Async batch-prediction worker for /v1/predict/batch
    │       └── retrain_task.py    # Drift-triggered retraining (Celery Beat, 24h)
    ├── tests/
    │   ├── unit/                  # Pure Python — no HTTP, no DB
    │   └── integration/           # Full stack with mock HTTP
    ├── frontend/
    │   ├── app.py                 # Main Streamlit dashboard
    │   └── pages/                 # fraud_scanner, live_feed, drift_monitor, history, system_health
    ├── docs/
    │   ├── API.md                 # REST + WS endpoint reference
    │   ├── ARCHITECTURE.md        # Detailed system architecture
    │   └── decisions/             # ADRs: rules-before-ml, shap-vs-lime, cost-threshold, llm-explainer
    ├── docker/
    │   ├── Dockerfile.backend     # Multi-stage Python 3.11-slim
    │   ├── Dockerfile.frontend
    │   └── prometheus.yml
    ├── docker-compose.yml         # 8 services: backend, frontend, postgres, redis, celery, celery-beat, prometheus, grafana
    ├── pyproject.toml             # Python 3.11+ deps + Ruff/Mypy config
    └── Makefile
```

## Environment Variables

Root app (`.env`):
- `HF_TOKEN` — HuggingFace token for Llama 3
- `API_KEY` — static key required for all endpoints (header: `x-api-key`)
- `FRONTEND_URL` — CORS origin (default: `http://localhost:8501`)

Sentinel service (`sentinel/.env`):
- `DATABASE_URL` — `postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel`
- `REDIS_URL` — `redis://localhost:6379`
- `HF_TOKEN`, `SECRET_KEY` (≥32 chars for JWT), `API_KEY`
- `MLFLOW_TRACKING_URI` — defaults to `sqlite:///mlflow.db`
- `MODEL_PATH` — path to MLflow artifact dir (default: `fraud_model`)
- `FRAUD_FP_COST` / `FRAUD_FN_COST` — cost matrix for threshold (default: `5.0` / `850.0`)
- `AB_CHALLENGER_PCT` — % traffic to challenger model (default: `10`)
- `DRIFT_THRESHOLD` — PSI threshold for retrain (default: `0.2`)

## ML Model Notes

- **Training data:** PaySim synthetic dataset (CSV) placed in `data/` — not in git. Only `CASH_OUT` and `TRANSFER` transactions are used.
- **Features (8):** `type` (encoded), `amount`, `oldbalanceOrg`, `newbalanceOrig`, `errorBalanceOrg`, `amount_to_balance_ratio`, `is_zero_balance_after`, `is_round_amount`.
- **Class imbalance:** handled with `scale_pos_weight=99`.
- **`fraud_model/` artifact** is not committed to git — rebuild with `make train` (sentinel) or `python rebuild_model.py` (root). The root `backend/main.py` also auto-rebuilds it on startup if missing.
- **A/B testing:** Champion required; challenger optional (set `CHALLENGER_MODEL_PATH` env var). Routing is deterministic per `customer_id` via MD5 hash.
- **Reference data** for drift monitoring is saved during training to `ml/reference_data.csv`.

## Observability

- **Prometheus:** http://localhost:9090 — metrics: `sentinel_predictions_total`, `sentinel_request_duration_seconds`, `sentinel_fraud_rate_1h`, `sentinel_model_confidence`
- **Grafana:** http://localhost:3000 (admin / sentinel)
- **Structured logs:** JSON via structlog with request ID correlation
- **WebSocket alerts:** `ws://localhost:8000/ws/alerts` — broadcasts all BLOCK decisions

## Code Quality

- **Ruff** (line length 100) + **Mypy strict** — run `make lint typecheck` before committing
- **Coverage floor:** 80% (`fail_under` in `pyproject.toml`)
- Unit tests must be pure Python with no HTTP or database dependencies
