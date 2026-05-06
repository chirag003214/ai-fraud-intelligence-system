# 🛡️ Sentinel: AI Fraud Intelligence Platform

A fraud detection system combining XGBoost, a deterministic rules engine, and LLM-powered explanations. The repo contains **two implementations**:

| Layer | Path | What it is |
|---|---|---|
| **Production stack** | [`sentinel/`](sentinel/) | Multi-service: FastAPI + PostgreSQL + Redis + Celery + WebSockets + Prometheus/Grafana, JWT auth, async SHAP/LLM workers, PSI drift monitoring, cost-aware thresholding, A/B model routing. **This is the system worth reviewing.** |
| **Single-process demo** | `backend/` + `frontend/` | Minimal FastAPI + Streamlit app that loads the same `fraud_model/` artifact. Useful for a quick local run; uses SQLite, no Redis/Celery. |

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)
![XGBoost](https://img.shields.io/badge/Model-XGBoost-orange)
![MLflow](https://img.shields.io/badge/MLOps-MLflow-blue)
![License](https://img.shields.io/badge/License-MIT-green)

For full architecture, request flow, and design decisions, see [`sentinel/README.md`](sentinel/README.md) and [`sentinel/docs/ARCHITECTURE.md`](sentinel/docs/ARCHITECTURE.md).

---

## How it works (single-process demo)

```
Transaction → Rules Engine → XGBoost Classifier → Llama 3 Explanation
```

| Layer | Method | Purpose |
|---|---|---|
| **Layer 1** | Heuristic rules | Catches obvious fraud instantly (Phantom Drain, Magic Money) |
| **Layer 2** | XGBoost classifier | Pattern-based ML detection on PaySim features |
| **Layer 3** | Llama 3-8B (HuggingFace) | Human-readable forensic explanation, post-hoc only |

## Tech Stack (single-process demo)

- **Backend:** FastAPI + Uvicorn, secured with API key auth
- **ML Model:** XGBoost (saved in MLflow artifact format via `mlflow.xgboost.save_model`)
- **GenAI:** Llama 3-8B via HuggingFace Inference API
- **Frontend:** Streamlit with fraud scanner, drift monitor, system health
- **Storage:** SQLite (transaction log + per-customer velocity counter)
- **Deployment:** Docker (root `Dockerfile`) → Render.com

> **Note:** MLflow run tracking, model registry, and Optuna HPO live in `sentinel/ml/`. The root `rebuild_model.py` only writes the artifact in MLflow format — it does not start an MLflow tracking run.

## Project Structure (root)
```
backend/
├── main.py               # FastAPI: prediction endpoint, rules, LLM explanation
├── database.py           # SQLite transaction log + velocity helpers
├── routers/              # predict.py, explain.py
├── services/model_loader.py
└── ...
frontend/
├── app.py                # Streamlit UI: fraud scanner
├── drift_monitor.py      # PSI-style feature drift visualisation
└── system_health.py      # API health dashboard
fraud_model/              # MLflow XGBoost artifact (NOT committed — see "Get the model")
rebuild_model.py          # Dev-only fallback trainer (synthetic data, see file header)
sentinel/                 # Production stack — see sentinel/README.md
```

## Quick Start (single-process demo)

**1. Clone**
```bash
git clone https://github.com/chirag003214/ai-fraud-intelligence-system
cd ai-fraud-intelligence-system
```

**2. Install backend + frontend deps**
```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

**3. Set environment variables**
```bash
cp .env.example .env
# Fill in HF_TOKEN and API_KEY in .env
```

**4. Get the model**

The trained `fraud_model/` artifact is **not committed** to git. You have three options:

- **Train on real data (recommended):** Download the [PaySim synthetic financial dataset](https://www.kaggle.com/datasets/ealaxi/paysim1) (`PS_20174392719_1491204439457_log.csv`), place it under `data/`, then run the production trainer:
  ```bash
  cd sentinel && make train
  ```
- **Dev fallback (no dataset needed):** `python rebuild_model.py` trains on a tiny synthetic stub purely so the API can boot. See the file header — this artifact is **not** suitable for evaluating fraud-detection quality.
- **Auto-rebuild on startup:** `backend/main.py` calls `_rebuild_model()` on startup if `fraud_model/` is missing. Same caveat as the dev fallback above.

**5. Run the backend**
```bash
uvicorn backend.main:app --reload --port 10000
```

**6. Run the frontend**
```bash
cd frontend
streamlit run app.py
```

Or run everything in one container:
```bash
docker build -t sentinel .
docker run -p 10000:10000 --env-file .env sentinel
```

## Key Design Decisions

- **Rules before ML** — known patterns (balance drops to zero without matching transfer) caught instantly, no model dependency.
- **LLM as explainer, not classifier** — Llama 3 only runs after the decision is made; never influences the prediction.
- **Cost-aware thresholding** — production stack uses `t* = FP_cost / (FP_cost + FN_cost)` instead of an arbitrary 0.5 cutoff. See [`sentinel/docs/decisions/003-cost-threshold.md`](sentinel/docs/decisions/003-cost-threshold.md).
- **API key auth** — backend secured; frontend passes the key via header, keeping it out of URLs.

## Dataset

Trained on the [PaySim synthetic financial dataset](https://www.kaggle.com/datasets/ealaxi/paysim1) (Kaggle). Place the CSV in `data/` before running `cd sentinel && make train`.

## Limitations / Honest Caveats

- The `fraud_model/` artifact is not in git — needs the PaySim dataset to rebuild properly. The auto-rebuild fallback in `backend/main.py` and `rebuild_model.py` uses synthetic stubs to make the API runnable; metrics from those models are not meaningful.
- The single-process demo (`backend/` + `frontend/`) uses SQLite and has no Redis, Celery, or WebSocket layer — for those, run the `sentinel/` stack.
- Root demo CORS is permissive (`*` by default); the `sentinel/` stack reads a configured `CORS_ORIGINS` list.
