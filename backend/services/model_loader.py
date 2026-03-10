import mlflow
import mlflow.sklearn

mlflow.set_tracking_uri("sqlite:///mlflow.db")

MODEL_NAME = "FraudDetectionRF"
_model = None

def get_model():
    global _model
    if _model is None:
        _model = mlflow.sklearn.load_model(
            f"models:/{MODEL_NAME}/latest"
        )
    return _model

