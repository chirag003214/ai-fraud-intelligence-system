import streamlit as st
import requests
import csv
import os
from datetime import datetime

# --- CONFIG ---
API_URL = "http://127.0.0.1:8000/predict"
st.set_page_config(page_title="FraudGuard", page_icon="🛡️", layout="wide")

st.title("🛡️ Sentinel: AI Fraud Intelligence Platform")

# Updated imports
import os
import csv
from datetime import datetime
def save_feedback(txn_data, prediction, feedback):
    # REVERTED TO RELATIVE PATH FOR CLOUD DEPLOYMENT
    file_path = "feedback_log.csv" 
    
    file_exists = os.path.isfile(file_path)
    
    try:
        with open(file_path, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "amount", "type", "prediction", "feedback"])
            
            writer.writerow([
                datetime.now(), 
                txn_data["amount"], 
                txn_data["type"], 
                prediction, 
                feedback
            ])
        # Removed the print statement with the hardcoded path
            
    except Exception as e:
        st.error(f"Error saving feedback: {e}")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("📝 Transaction Details")
    txn_type = st.selectbox("Transaction Type", ["CASH_OUT", "TRANSFER"])
    amount = st.number_input("Amount ($)", min_value=0.0, value=5000.0, step=100.0)
    old_bal = st.number_input("Sender Old Balance ($)", min_value=0.0, value=5000.0)
    new_bal = st.number_input("Sender New Balance ($)", min_value=0.0, value=0.0)
    
    analyze_btn = st.button("Analyze Risk", type="primary")

# --- MAIN PAGE LOGIC ---
if analyze_btn:
    payload = {
        "type": txn_type,
        "amount": amount,
        "oldbalanceOrg": old_bal,
        "newbalanceOrig": new_bal
    }
    
    try:
        with st.spinner("Scanning transaction patterns..."):
            response = requests.post(API_URL, json=payload)
            
        if response.status_code == 200:
            data = response.json()
            
            col1, col2 = st.columns(2)
            
            # RESULT COLUMN
            with col1:
                st.subheader("Risk Analysis")
                if data["is_fraud"] == 1:
                    st.error("🚨 HIGH RISK DETECTED")
                    st.metric("Risk Level", "CRITICAL")
                else:
                    st.success("✅ SAFE TRANSACTION")
                    st.metric("Risk Level", "NORMAL")
            
            # EXPLANATION COLUMN
            with col2:
                st.subheader("AI Insight (Llama 3)")
                st.info(data["explanation"])
                
            st.divider()
            
            # FEEDBACK LOOP
            st.write("👮 **Investigator Feedback (Human-in-the-Loop)**")
            f1, f2 = st.columns([1,4])
            with f1:
                if st.button("👍 Correct"):
                    save_feedback(payload, data["is_fraud"], "Correct")
                    st.toast("Feedback Saved: Model Reinforced.")
            with f2:
                if st.button("👎 Incorrect"):
                    save_feedback(payload, data["is_fraud"], "Incorrect")
                    st.toast("Feedback Saved: Flagged for Retraining.")
                    
        else:
            st.error("API Error: Could not get prediction.")
            
    except Exception as e:
        st.error(f"Connection Error: {e}. Is the Backend running?")