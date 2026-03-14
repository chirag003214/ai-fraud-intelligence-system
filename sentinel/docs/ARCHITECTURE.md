# Sentinel Architecture

## System Overview

```
┌──────────────┐    ┌─────────────────────────────────────────────┐
│   Streamlit   │───▶│  FastAPI Backend (Sentinel API v2.0)        │
│   Dashboard   │◀───│                                             │
│   :8501       │    │  ┌─────────┐  ┌────────┐  ┌────────────┐  │
└──────────────┘    │  │ Routes  │─▶│Services│─▶│ ML Pipeline │  │
                    │  └─────────┘  └────────┘  └────────────┘  │
                    │       │            │             │          │
                    │  ┌────▼────┐  ┌───▼───┐   ┌───▼────┐     │
                    │  │ Auth    │  │ Redis │   │ Model  │     │
                    │  │ JWT/Key │  │:6379  │   │Registry│     │
                    │  └─────────┘  └───────┘   └────────┘     │
                    │       │                                    │
                    │  ┌────▼────────────────────────────┐      │
                    │  │  PostgreSQL :5432                │      │
                    │  │  (transactions, explanations)    │      │
                    │  └─────────────────────────────────┘      │
                    └─────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Celery Workers    │
                    │  ┌──────────────┐  │
                    │  │ SHAP Task    │  │
                    │  │ LLM Task     │  │
                    │  │ Batch Task   │  │
                    │  │ Retrain Task │  │
                    │  └──────────────┘  │
                    └───────────────────┘
```

## Request Flow

1. Transaction arrives at `POST /v1/predict`
2. Authentication checked (JWT or API key)
3. Velocity counter incremented in Redis (O(1))
4. Rules engine evaluates hard rules (Phantom Drain, Magic Money)
5. Feature engineering transforms raw data
6. XGBoost model produces fraud probability
7. Cost-aware threshold converts probability to decision
8. Decision fusion combines rules + ML + velocity
9. Result persisted to PostgreSQL
10. If BLOCK: WebSocket broadcast to all dashboards
11. SHAP + LLM explanation queued to Celery (non-blocking)
12. Response returned to client

## Key Design Decisions

See [docs/decisions/](decisions/) for detailed ADRs:
- [001 — Rules Before ML](decisions/001-rules-before-ml.md)
- [002 — SHAP vs LIME](decisions/002-shap-vs-lime.md)
- [003 — Cost Threshold](decisions/003-cost-threshold.md)
- [004 — LLM as Explainer](decisions/004-llm-as-explainer.md)
