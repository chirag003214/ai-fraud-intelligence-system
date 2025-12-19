import pandas as pd
import mlflow.pyfunc
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# 1. Load Secrets
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
API_SECRET_KEY = os.getenv("API_KEY", "Sentinel_Secure_2025") # Must match Frontend

# 2. Setup App & Security
app = FastAPI(title="Sentinel: AI Fraud Intelligence Platform")

# CORS (Allow Frontend to talk to Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace * with your specific Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Scheme
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="⛔ Access Denied: Invalid API Key")
    return api_key_header

# 3. Define Data Structure (Matches PaySim Dataset)
class Transaction(BaseModel):
    type: str  # "CASH_OUT" or "TRANSFER"
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float

# 4. Global Model Variable
model = None
MODEL_PATH = "fraud_model" # Folder where we exported the model

@app.on_event("startup")
def load_model():
    global model
    try:
        print(f"📂 Loading model from '{MODEL_PATH}'...")
        model = mlflow.pyfunc.load_model(MODEL_PATH)
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

# 5. GenAI Explanation Function (Llama 3)
def explain_fraud(txn: Transaction, risk_score: str, rule_hit: str = None):
    if not HF_TOKEN:
        return "Explanation unavailable (HF_TOKEN missing)."
    
    client = InferenceClient(token=HF_TOKEN)
    
    # Prompt Engineering
    prompt = f"""
    You are a financial fraud investigator. Analyze this suspicious transaction:
    - Type: {txn.type}
    - Amount: ${txn.amount}
    - Sender Old Balance: ${txn.oldbalanceOrg}
    - Sender New Balance: ${txn.newbalanceOrig}
    - Alert: {rule_hit if rule_hit else "ML Model detected anomaly"}
    
    Explain in 1 clear sentence why this is risky. Do not define terms. Focus on the math.
    """
    
    try:
        response = client.text_generation(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            prompt=prompt,
            max_new_tokens=60,
            temperature=0.7
        )
        return response.strip()
    except Exception as e:
        return f"AI Analysis failed: {str(e)}"

# 6. The Secured Predict Endpoint
@app.post("/predict")
def predict(txn: Transaction, api_key: str = Depends(get_api_key)):
    global model
    if not model:
        raise HTTPException(status_code=500, detail="Model is not loaded.")

    # --- A. HARD RULES LAYER (Heuristics) ---
    # Rule 1: Phantom Drain (Money disappears but wasn't sent)
    if txn.amount > 0 and txn.oldbalanceOrg > 0 and txn.newbalanceOrig == 0:
        if txn.amount != txn.oldbalanceOrg:
             return {
                "is_fraud": 1,
                "risk_score": "CRITICAL",
                "explanation": "HARD RULE VIOLATION: Phantom Drain detected. Balance dropped to zero without matching transfer amount."
            }

    # Rule 2: Magic Money (Balance increases after sending money)
    if txn.newbalanceOrig > txn.oldbalanceOrg:
         return {
            "is_fraud": 1,
            "risk_score": "CRITICAL",
            "explanation": "HARD RULE VIOLATION: Magic Money. Sender balance increased after an outflow transaction."
        }

    # --- B. ML PREDICTION LAYER ---
    try:
        # 1. Preprocess Data (Must match Training Logic!)
        input_data = pd.DataFrame([txn.dict()])
        
        # Calculate Error Balance (Feature Engineering)
        input_data['errorBalanceOrg'] = input_data.newbalanceOrig + input_data.amount - input_data.oldbalanceOrg
        
        # Label Encode Type (CASH_OUT=0, TRANSFER=1) - Logic from your training script
        type_map = {'CASH_OUT': 0, 'TRANSFER': 1, 'PAYMENT': 3, 'CASH_IN': 4, 'DEBIT': 5}
        input_data['type'] = input_data['type'].map(type_map).fillna(0) # Default to 0 if unknown
        
        # Select Features expected by XGBoost
        features = ['type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'errorBalanceOrg']
        input_data = input_data[features]

        # 2. Predict
        prediction = model.predict(input_data)[0]
        is_fraud = int(prediction)
        
        # 3. Generate Explanation
        explanation = "Transaction appears normal."
        if is_fraud:
            explanation = explain_fraud(txn, "CRITICAL")
            
        return {
            "is_fraud": is_fraud,
            "risk_score": "CRITICAL" if is_fraud else "SAFE",
            "explanation": explanation
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")

# 7. Health Check (For System Health Page)
@app.get("/")
def home():
    return {"status": "online", "model_loaded": model is not None}