import pandas as pd
import mlflow.pyfunc
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Import Database Functions
from backend.database import init_db, log_transaction, get_customer_velocity, get_recent_transactions

# 1. Load Secrets
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
API_SECRET_KEY = os.getenv("API_KEY")
if not API_SECRET_KEY:
    raise RuntimeError("API_KEY environment variable not set")

# 2. Setup App
app = FastAPI(title="Sentinel Pro: Context-Aware Fraud Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Security Dependency (Must be defined BEFORE predict function)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="⛔ Access Denied: Invalid API Key")
    return api_key_header

# 4. Data Models
class Transaction(BaseModel):
    customer_id: str   # For velocity tracking
    ip_address: str    # For auditing
    type: str
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float

# 5. Global State
model = None
MODEL_PATH = "fraud_model"

@app.on_event("startup")
def startup_event():
    global model
    try:
        # Load ML Model
        model = mlflow.pyfunc.load_model(MODEL_PATH)
        # Initialize Database
        init_db()
        print("✅ System Online: Model Loaded + DB Connected")
    except Exception as e:
        print(f"❌ Startup Error: {e}")

# 6. AI Explanation Helper
def explain_fraud(txn: Transaction, risk_reason: str, velocity: int):
    """Use Llama 3 to explain risk."""
    if not HF_TOKEN: return "AI Explanation Unavailable."
    
    client = InferenceClient(token=HF_TOKEN)
    
    messages = [
        {"role": "system", "content": "You are a senior fraud analyst. Summarize risk in 1 sentence."},
        {"role": "user", "content": f"""
        Analyze transaction:
        - User: {txn.customer_id}
        - Amount: ${txn.amount}
        - Velocity (1h): {velocity}
        - Signals: {risk_reason}
        """}
    ]
    
    try:
        response = client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=messages, 
            max_tokens=80
        )
        return response.choices[0].message.content.strip()
    except:
        return "Manual Review Required."

# 7. Prediction Endpoint
@app.post("/predict")
def predict(txn: Transaction, api_key: str = Depends(get_api_key)):
    global model
    if not model: raise HTTPException(status_code=500, detail="Model inactive")

    # --- PHASE 1: CONTEXT (Velocity Check) ---
    velocity = get_customer_velocity(txn.customer_id)
    # Count includes current one, so if > 5 it's high
    is_high_velocity = velocity >= 5  
    
    # --- PHASE 2: ML INFERENCE ---
    input_data = pd.DataFrame([{
        'type': txn.type, 
        'amount': txn.amount, 
        'oldbalanceOrg': txn.oldbalanceOrg, 
        'newbalanceOrig': txn.newbalanceOrig
    }])
    
    # Feature Engineering
    input_data['errorBalanceOrg'] = input_data.newbalanceOrig + input_data.amount - input_data.oldbalanceOrg
    type_map = {'CASH_OUT': 0, 'TRANSFER': 1, 'PAYMENT': 3, 'CASH_IN': 4, 'DEBIT': 5}
    input_data['type'] = input_data['type'].map(type_map).fillna(0)
    
    # Predict
    ml_fraud = int(model.predict(input_data[['type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'errorBalanceOrg']])[0])

    # --- PHASE 3: DECISION LOGIC ---
    action = "ALLOW"
    risk_score = "LOW"
    reasons = []

    if ml_fraud:
        action = "BLOCK"
        risk_score = "CRITICAL"
        reasons.append("ML Pattern Match")
    
    if is_high_velocity:
        action = "CHALLENGE" if action == "ALLOW" else "BLOCK"
        risk_score = "HIGH" if risk_score == "LOW" else "CRITICAL"
        reasons.append(f"High Velocity ({velocity} txns/hr)")

    if txn.amount > 100000:
        reasons.append("Large Value")

    # Finalize
    final_reason = ", ".join(reasons) if reasons else "Normal Behavior"
    explanation = explain_fraud(txn, final_reason, velocity)

    # Log to DB
    log_transaction(txn.customer_id, txn.ip_address, txn, risk_score, int(is_high_velocity), explanation)

    return {
        "action": action,
        "risk_score": risk_score,
        "reasons": reasons,
        "velocity_1h": velocity,
        "explanation": explanation
    }

# 8. History Endpoint
@app.get("/history")
def get_history(api_key: str = Depends(get_api_key)):
    df = get_recent_transactions(limit=50)
    return df.to_dict(orient="records")