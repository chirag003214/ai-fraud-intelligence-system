import streamlit as st
import requests
import json
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="Sentinel: AI Fraud Guard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2058/2058768.png", width=100)
st.sidebar.title("Sentinel Pro")

# Navigation Menu
menu = st.sidebar.radio(
    "Navigation", 
    ["Fraud Scanner", "System Health", "Drift Monitor"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **Enterprise Status**
    
    - ⚡ **Model:** XGBoost + Llama 3
    - 🔒 **Encryption:** TLS 1.3
    - 🟢 **System:** Online
    """
)

# --- 1. FRAUD SCANNER PAGE ---
if menu == "Fraud Scanner":
    st.title("🛡️ Sentinel: Transaction Guard")
    st.markdown("### Real-Time Financial Intelligence Gateway")

    # Split layout: Input Form (Left) vs. Results (Right)
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Transaction Details")
        with st.form("prediction_form"):
            
            # INPUTS MATCHING YOUR BACKEND MODEL (PaySim Dataset)
            type_val = st.selectbox("Transaction Type", ["CASH_OUT", "TRANSFER", "PAYMENT", "CASH_IN", "DEBIT"])
            amount = st.number_input("Transaction Amount ($)", min_value=0.0, value=10000.0, step=100.0)
            old_balance = st.number_input("Sender Old Balance ($)", min_value=0.0, value=10000.0, step=100.0)
            new_balance = st.number_input("Sender New Balance ($)", min_value=0.0, value=0.0, step=100.0)
            
            st.markdown("---")
            st.caption("🔒 Data is encrypted end-to-end.")
            submit_button = st.form_submit_button("🔍 Scan Transaction", type="primary")

    with col2:
        st.subheader("📊 Intelligence Report")
        
        if submit_button:
            # 1. Prepare Payload
            payload = {
                "type": type_val,
                "amount": amount,
                "oldbalanceOrg": old_balance,
                "newbalanceOrig": new_balance
            }
            
            # 2. Get Configuration (Cloud or Local)
            # Use your Render URL here. If testing locally, use "http://127.0.0.1:8000/predict"
            API_URL = os.getenv("API_URL", "https://ai-fraud-intelligence-system.onrender.com/predict")
            API_KEY = os.getenv("API_KEY", "Sentinel_Secure_2025") # Ensure this matches your Backend!
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": API_KEY
            }
            
            # 3. Call the API
            with st.spinner("🔄 Analyzing patterns & generating Llama 3 explanation..."):
                try:
                    response = requests.post(API_URL, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Parse Response
                        is_fraud = result.get("is_fraud", 0)
                        risk_score = "CRITICAL" if is_fraud else "SAFE"
                        explanation = result.get("explanation", "No explanation generated.")
                        
                        # --- DISPLAY RESULTS ---
                        if is_fraud:
                            st.error("🚨 **FRAUD DETECTED**")
                            st.metric(label="Risk Level", value="CRITICAL", delta="-100%", delta_color="inverse")
                            st.markdown(f"**Action Required:** Block Transaction & Flag User ID.")
                        else:
                            st.success("✅ **LEGITIMATE TRANSACTION**")
                            st.metric(label="Risk Level", value="SAFE", delta="100%")
                        
                        # --- AI EXPLANATION SECTION ---
                        st.markdown("#### 🧠 AI Forensic Analysis (Llama 3)")
                        st.info(explanation)
                        
                        # --- VISUALIZATION (Context Graph) ---
                        st.markdown("#### 📉 Transaction Context")
                        chart_data = pd.DataFrame({
                            "Metric": ["Amount", "Old Balance", "New Balance"],
                            "Value": [amount, old_balance, new_balance]
                        })
                        st.bar_chart(chart_data.set_index("Metric"))
                        
                    elif response.status_code == 403:
                        st.error("⛔ **Access Denied:** Invalid API Key.")
                    else:
                        st.error(f"⚠️ Server Error ({response.status_code}): {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ **Connection Error:** Could not reach the Backend. Is it running?")
                except Exception as e:
                    st.error(f"❌ **Error:** {e}")

        else:
            # Default state when no data is submitted
            st.info("👈 Enter transaction details to generate a real-time risk assessment.")
            st.markdown(
                """
                **Supported Detection Models:**
                * *XGBoost Classifier* (Pattern Recognition)
                * *Heuristic Rules Engine* (Hard Logic)
                * *Llama 3-8B* (Reasoning & Explanations)
                """
            )

# --- 2. SYSTEM HEALTH PAGE ---
elif menu == "System Health":
    try:
        import system_health
        system_health.show_health()
    except ImportError:
        st.error("⚠️ `system_health.py` not found. Please create the file.")

# --- 3. DRIFT MONITOR PAGE ---
elif menu == "Drift Monitor":
    try:
        import drift_monitor
        drift_monitor.show_drift()
    except ImportError:
        st.error("⚠️ `drift_monitor.py` not found. Please create the file.")

# --- FOOTER ---
st.markdown("---")
st.caption("Sentinel AI v2.0 | Engineered by Chirag Sharma")