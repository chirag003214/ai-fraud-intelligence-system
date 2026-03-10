# 🛡️ Sentinel: AI Fraud Intelligence Platform

A production-style fraud detection system combining XGBoost ML, heuristic 
rules, and LLM-powered explanations via a FastAPI backend and Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)
![XGBoost](https://img.shields.io/badge/Model-XGBoost-orange)
![MLflow](https://img.shields.io/badge/MLOps-MLflow-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## How it works
```
Transaction → Hard Rules Engine → XGBoost Classifier → Llama 3 Explanation
```

Three-layer detection pipeline:

| Layer | Method | Purpose |
|---|---|---|
| **Layer 1** | Heuristic rules | Catches obvious fraud instantly (Phantom Drain, Magic Money) |
| **Layer 2** | XGBoost classifier | Pattern-based ML detection on PaySim features |
| **Layer 3** | Llama 3-8B (HuggingFace) | Human-readable forensic explanation |

## Tech Stack

- **Backend:** FastAPI + Uvicorn, secured with API key auth
- **ML Model:** XGBoost trained on PaySim financial dataset
- **MLOps:** MLflow model registry + artifact tracking
- **GenAI:** Llama 3-8B via HuggingFace Inference API
- **Frontend:** Streamlit with fraud scanner, drift monitor, system health
- **Deployment:** Docker + Render.com

## Project Structure
```
backend/main.py          — FastAPI app: prediction endpoint, rules engine, LLM explanation
scripts/train.py         — XGBoost training with MLflow experiment tracking
frontend/app.py          — Streamlit UI: fraud scanner, navigation
frontend/drift_monitor.py — PSI-based feature drift visualization
frontend/system_health.py — API health metrics dashboard
fraud_model/             — Exported MLflow model artifact (see Setup)
export_model.py          — Copies latest MLflow model to fraud_model/
model_rebuild.py         — Retrain from scratch if model.pkl is missing
```

## Quick Start

**1. Clone and install**
```bash
git clone https://github.com/chirag003214/ai-fraud-intelligence-system
cd ai-fraud-intelligence-system
pip install -r requirements.txt
```

**2. Set environment variables**
```bash
cp .env.example .env
# Fill in HF_TOKEN and API_KEY in .env
```

**3. Get the model**

The trained model is not stored in git (binary file). Rebuild it:
```bash
# Place the PaySim dataset CSV inside a data/ folder, then:
python model_rebuild.py
```
Or if MLflow already has a registered run:
```bash
python export_model.py
```

**4. Run the backend**
```bash
uvicorn backend.main:app --reload --port 10000
```

**5. Run the frontend**
```bash
cd frontend
streamlit run app.py
```

Or run everything with Docker:
```bash
docker build -t sentinel .
docker run -p 10000:10000 --env-file .env sentinel
```

## Key Design Decisions

- **Hard rules before ML:** Obvious fraud patterns (balance drops to zero 
  without matching transfer) are caught instantly without a model call — 
  faster and more reliable for known attack vectors
- **MLflow model registry:** Model is versioned and exported cleanly; 
  `model_rebuild.py` lets anyone regenerate the artifact from the raw dataset
- **LLM as explainer, not classifier:** Llama 3 only runs after the 
  decision is made — used purely to generate a human-readable explanation, 
  keeping the core prediction fast and deterministic
- **API key auth:** Backend is secured; frontend passes the key via 
  request header, keeping it out of the URL

## Dataset

Trained on the [PaySim synthetic financial dataset](https://www.kaggle.com/datasets/ealaxi/paysim1).  
Place the CSV in `data/` before running `model_rebuild.py`.

## Limitations / Future Work

- `model.pkl` not tracked in git — requires dataset to rebuild locally 
  (would use Git LFS or an S3 download script in production)
- Drift monitor uses simulated data — would connect to a real transaction 
  log in production using Evidently AI
- CORS is currently open (`*`) — would restrict to frontend URL in production
