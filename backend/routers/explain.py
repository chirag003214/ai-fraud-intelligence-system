from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pickle
import numpy as np
from shapash.explainer.smart_explainer import SmartExplainer

router = APIRouter()

# ------------------------------
# Load trained ML model
# ------------------------------
MODEL_PATH = "backend/models/fraud_model.pkl"

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except Exception as e:
    model = None
    print("Model loading failed:", e)

# ------------------------------
# Create SmartExplainer safely
# ------------------------------
explainer = None
X_train_sample = None  # Placeholder — will be passed when model training notebook is done

def initialize_explainer():
    global explainer, X_train_sample, model

    if model is None:
        print("⚠ Model not loaded yet.")
        return None

    if X_train_sample is None:
        # temporary dummy data; replaced after training notebook
        X_train_sample = np.random.rand(100, 10)

    explainer = SmartExplainer(model=model)
    explainer.compile(x=X_train_sample)

initialize_explainer()

# ------------------------------
# API Input Schema
# ------------------------------
class ExplainRequest(BaseModel):
    features: list

# ------------------------------
# SHAPASH Explanation Endpoint
# ------------------------------
@router.post("/explain/local")
def explain_local(req: ExplainRequest):
    if model is None:
        raise HTTPException(status_code=400, detail="Model not loaded yet.")

    if explainer is None:
        initialize_explainer()

    try:
        x = np.array(req.features).reshape(1, -1)

        # SmartExplainer local explanation
        exp = explainer.explain_local(x)

        return {
            "explanation": exp.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    
