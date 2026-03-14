<div align="center">

# 🛡️ Sentinel — AI Fraud Intelligence Platform

### Production-grade fraud detection that catches what rules miss and explains what models find.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange.svg)](https://xgboost.readthedocs.io)
[![SHAP](https://img.shields.io/badge/Explainability-SHAP-purple.svg)](https://shap.readthedocs.io)
[![MLflow](https://img.shields.io/badge/MLOps-MLflow-0194E2.svg)](https://mlflow.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Cost-aware thresholding** · **Real-time WebSocket alerts** · **A/B model testing** · **Async SHAP + LLM explanations**

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [API Reference](docs/API.md) · [Contributing](CONTRIBUTING.md)

</div>

---

## 🎯 What makes this different?

Most fraud detection demos are a model + an endpoint. Sentinel is the **full production stack**:

| Feature | Why it matters |
|---|---|
| **4-stage pipeline** | Rules → ML → Cost threshold → Decision fusion |
| **Cost-aware threshold** | Not 0.5 — derived from `FP_cost / (FP_cost + FN_cost)` |
| **A/B model routing** | Deterministic champion/challenger split per customer |
| **Async explanations** | SHAP + LLM computed in background, prediction returns <100ms |
| **Real drift monitoring** | PSI computation on live data, not `numpy.random` |
| **WebSocket live feed** | BLOCK decisions broadcast to all dashboards in real-time |
| **Structured logging** | JSON logs with request IDs, not `print()` statements |
| **Prometheus metrics** | Latency histograms, confidence distributions, fraud rates |

---

## 🏗️ Architecture

```
Transaction ──▶ Rules Engine ──▶ XGBoost ──▶ Cost Threshold ──▶ Decision
                     │               │              │               │
                Phantom Drain    Feature Eng.    t*=FP/(FP+FN)   ALLOW
                Magic Money      predict_proba   calibrated      CHALLENGE
                Large Value      confidence       clamped         BLOCK
                     │               │                              │
                     └───── Velocity (Redis O(1)) ──────────────────┘
                                                                    │
                              ┌─────────────────────────────────────┘
                              ▼
                    ┌──── Persist to PostgreSQL
                    ├──── WebSocket broadcast (if BLOCK)
                    └──── Queue SHAP + LLM (Celery, async)
```

---

## 🚀 Quick Start

### One command (Docker)

```bash
cd sentinel
make dev
```

This starts: **Backend** (:8000) · **Frontend** (:8501) · **PostgreSQL** · **Redis** · **Celery** · **Prometheus** (:9090) · **Grafana** (:3000)

### Manual setup

```bash
# 1. Clone and install
git clone https://github.com/chirag003214/ai-fraud-intelligence-system
cd ai-fraud-intelligence-system/sentinel
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Start dependencies
docker-compose up -d postgres redis

# 4. Run the backend
uvicorn sentinel.src.api.main:app --reload --port 8000

# 5. Run the frontend
cd frontend && streamlit run app.py
```

### Test the prediction

```bash
curl -X POST http://localhost:8000/v1/predict \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "TEST_001",
    "ip_address": "1.1.1.1",
    "type": "TRANSFER",
    "amount": 95000,
    "oldbalanceOrg": 95000,
    "newbalanceOrig": 0
  }'
```

**Response:**
```json
{
  "transaction_id": "a1b2c3d4-...",
  "action": "BLOCK",
  "risk_score": "CRITICAL",
  "confidence": 0.94,
  "decision_threshold": 0.1,
  "reasons": ["Phantom Drain", "ML Score 0.94 ≥ threshold 0.10"],
  "velocity_1h": 1,
  "model_version": "latest",
  "ab_variant": "champion"
}
```

---

## 📁 Project Structure

```
sentinel/
├── src/                          # Backend application
│   ├── api/                      # FastAPI routes and middleware
│   │   ├── main.py               # App factory with lifespan
│   │   ├── deps.py               # Dependency injection (DB, Redis, auth)
│   │   ├── middleware.py          # Request ID, Prometheus metrics
│   │   └── routes/               # Endpoint handlers
│   ├── services/                 # Business logic (zero FastAPI imports)
│   │   ├── detection.py          # Rules → ML → threshold → decision
│   │   ├── velocity.py           # Redis O(1) transaction counting
│   │   ├── drift.py              # PSI computation
│   │   ├── explainer.py          # Async SHAP + LLM pipeline
│   │   └── websocket_manager.py  # Real-time alert broadcasting
│   ├── core/                     # Infrastructure
│   │   ├── config.py             # pydantic-settings (all env vars typed)
│   │   ├── database.py           # Async SQLAlchemy + PostgreSQL
│   │   ├── redis_client.py       # Async Redis pool
│   │   └── security.py           # JWT + API key auth
│   └── schemas/                  # Pydantic request/response models
├── ml/                           # ML pipeline
│   ├── features.py               # Feature engineering + cost threshold
│   ├── loader.py                 # Model registry (champion/challenger)
│   ├── ab_test.py                # Deterministic A/B routing
│   ├── train.py                  # Full PaySim training pipeline
│   ├── evaluate.py               # PR-AUC, calibration, cost curves
│   └── tune.py                   # Optuna 50-trial HPO
├── workers/                      # Celery background tasks
│   ├── tasks/shap_task.py        # Async SHAP TreeExplainer
│   ├── tasks/llm_task.py         # Async LLM narrative (Llama 3)
│   └── tasks/retrain_task.py     # Drift-triggered retrain
├── tests/                        # Pytest suite (unit + integration)
├── frontend/                     # Streamlit dashboard
├── docker/                       # Dockerfiles + Grafana dashboards
├── docs/                         # Architecture + ADRs + API reference
├── docker-compose.yml            # Full stack in one command
├── pyproject.toml                # Dependencies + tool config
└── Makefile                      # Developer shortcuts
```

---

## 🧪 Testing

```bash
make test          # Full suite with coverage
make test-unit     # Unit tests only
make test-int      # Integration tests only
make lint          # Ruff linting
make typecheck     # Mypy strict mode
```

---

## 📊 Observability

| Tool | URL | Purpose |
|---|---|---|
| **Swagger UI** | http://localhost:8000/docs | Interactive API docs |
| **Prometheus** | http://localhost:9090 | Metrics storage |
| **Grafana** | http://localhost:3000 | Dashboards (admin/sentinel) |
| **Streamlit** | http://localhost:8501 | Fraud analyst dashboard |

---

## 🔑 Key Design Decisions

| Decision | Rationale |
|---|---|
| [Rules before ML](docs/decisions/001-rules-before-ml.md) | Known patterns caught without model dependency |
| [SHAP over LIME](docs/decisions/002-shap-vs-lime.md) | Exact explanations for tree models |
| [Cost threshold](docs/decisions/003-cost-threshold.md) | $5 FP vs $850 FN drives optimal cutoff |
| [LLM as explainer](docs/decisions/004-llm-as-explainer.md) | Post-hoc narrative, never influences prediction |

---

## 📈 Dataset

Trained on the [PaySim synthetic financial dataset](https://www.kaggle.com/datasets/ealaxi/paysim1).
Place the CSV in `data/` and run `make train` to rebuild the model.

---

## 🛡️ Security

- JWT + API key dual authentication
- Rate limiting (60 req/min on predict)
- CORS restricted to configured origins
- No secrets in code — all env vars
- Request ID injection for audit trails

---

<div align="center">

**Built by [Chirag Sharma](https://github.com/chirag003214)** · MIT License

</div>
