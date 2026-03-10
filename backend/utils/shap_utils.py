import shap
import pickle
import numpy as np


def load_model(path="backend/models/fraud_model.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)


def compute_shap_values(model, features):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(np.array(features).reshape(1, -1))
    return shap_values
