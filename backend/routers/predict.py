from fastapi import APIRouter
from pydantic import BaseModel
import numpy as np
from backend.services.model_loader import get_model

router = APIRouter(prefix="/api")

class Transaction(BaseModel):
    features: list[float]

@router.post("/predict")
def predict_fraud(transaction: Transaction):
    """
    Predict fraud probability from input features.
    """
    model = get_model()

    features = np.array(transaction.features).reshape(1, -1)

    probability = float(model.predict_proba(features)[0][1])
    prediction = bool(model.predict(features)[0])

    return {
        "fraud_probability": probability,
        "is_fraud": prediction
    }

