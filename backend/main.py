import pandas as pd
import mlflow.pyfunc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Fraud Guard API")

# --- CONFIGURATION ---
# ⚠️ REPLACE THIS WITH YOUR ACTUAL HUGGING FACE TOKEN
# Ensure this token has "Inference" permissions!
HF_TOKEN = os.getenv("HF_TOKEN")

# Setup Hugging Face Client (Llama 3 Instruct)
repo_id = "meta-llama/Meta-Llama-3-8B-Instruct"
llm_client = InferenceClient(model=repo_id, token=HF_TOKEN)

MODEL_NAME = "FraudGuard"
model = None

# --- LOAD MODEL AT STARTUP ---
@app.on_event("startup")
def load_model():
    global model
    try:
        model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/latest")
        print(f"✅ Model '{MODEL_NAME}' loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

# --- 1. DEFINE DATA SCHEMA ---
class Transaction(BaseModel):
    type: str
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float

# --- GENAI EXPLANATION FUNCTION ---
def generate_explanation(amount, old_bal, type_str):
    if not HF_TOKEN or "hf_" not in HF_TOKEN:
        return "AI Explanation unavailable (Invalid HF Token)."
    
    messages = [
        {
            "role": "system", 
            "content": "You are a fraud analyst. Explain why this transaction is suspicious in 1 short sentence."
        },
        {
            "role": "user", 
            "content": f"Transaction Details:\n- Type: {type_str}\n- Amount: ${amount}\n- Old Balance: ${old_bal}"
        }
    ]

    try:
        response = llm_client.chat_completion(
            messages=messages, 
            max_tokens=100, 
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

# --- 2. PREDICT ENDPOINT ---
@app.post("/predict")
def predict(txn: Transaction):
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # --- 🛡️ LAYER 1: HARD RULES (The Logic Check) ---
    
    # Rule 1: Overdraft Check
    if txn.amount > txn.oldbalanceOrg:
        return {
            "is_fraud": 1, 
            "risk_score": "CRITICAL", 
            "explanation": f"HARD RULE VIOLATION: Attempted to transfer ${txn.amount} with only ${txn.oldbalanceOrg} in account."
        }
    
    # Rule 2: Negative Numbers
    if txn.amount < 0 or txn.oldbalanceOrg < 0:
         return {
            "is_fraud": 1, 
            "risk_score": "CRITICAL", 
            "explanation": "HARD RULE VIOLATION: Negative transaction values detected."
        }

    # Rule 3: The "Math Integrity" Check (Catches Magic Money Increases)
    expected_balance = txn.oldbalanceOrg - txn.amount
    # If New Balance is significantly higher than expected (allowing small buffer)
    if txn.newbalanceOrig > (expected_balance + 2000): 
         return {
            "is_fraud": 1,
            "risk_score": "CRITICAL",
            "explanation": f"HARD RULE VIOLATION: Suspicious balance increase. Expected ~${expected_balance}, but got ${txn.newbalanceOrig}."
        }
    expected_balance = txn.oldbalanceOrg - txn.amount
    math_error = abs(txn.newbalanceOrig - expected_balance) # Use Absolute Difference
    
    if math_error > 200: # If off by more than $200 in EITHER direction
         return {
            "is_fraud": 1,
            "risk_score": "CRITICAL",
            "explanation": f"HARD RULE VIOLATION: Balance mismatch. Expected ~${expected_balance}, but difference is ${math_error:.2f}."
        }
    # Rule 4: The "Account Drain" Policy
    # Logic: If a transaction empties >90% of funds AND the amount is tiny (<$200) left, flag it.
    if txn.oldbalanceOrg > 0:
        draining_ratio = txn.amount / txn.oldbalanceOrg
        if draining_ratio > 0.90 and txn.newbalanceOrig < 200:
             return {
                "is_fraud": 1,
                "risk_score": "CRITICAL",
                "explanation": f"HARD RULE VIOLATION: Possible Account Draining. User withdrew {draining_ratio*100:.1f}% of funds."
            }
    # --- 🧠 LAYER 2: ML MODEL (The Pattern Check) ---
    type_val = 0 if txn.type == "CASH_OUT" else 1
    error_balance = txn.newbalanceOrig + txn.amount - txn.oldbalanceOrg

    input_df = pd.DataFrame([{
        "type": type_val,
        "amount": txn.amount,
        "oldbalanceOrg": txn.oldbalanceOrg,
        "newbalanceOrig": txn.newbalanceOrig,
        "errorBalanceOrg": error_balance
    }])

    # Predict
    prediction = int(model.predict(input_df)[0])
    
    # Explain
    explanation = "Transaction appears safe."
    if prediction == 1:
        explanation = generate_explanation(txn.amount, txn.oldbalanceOrg, txn.type)

    return {
        "is_fraud": prediction,
        "risk_score": "HIGH" if prediction == 1 else "LOW",
        "explanation": explanation
    }