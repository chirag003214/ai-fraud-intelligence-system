"""
Sentinel Streamlit Dashboard — refactored from the original frontend/app.py.

Preserves all existing functionality while updating API calls to use
the new v1 endpoints and adding the Live Feed page.
"""

import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page Configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinel: AI Fraud Guard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2058/2058768.png", width=100)
st.sidebar.title("Sentinel Pro")

menu = st.sidebar.radio(
    "Navigation",
    ["Fraud Scanner", "Live Feed", "Transaction History", "Drift Monitor", "System Health"],
)

st.sidebar.markdown("---")
st.sidebar.info("Enterprise Status: \n 🟢 Online | 🔒 Encrypted")

# ── API Configuration ────────────────────────────────────────────────
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "")
HEADERS = {"x-api-key": API_KEY}

# ── 1. Fraud Scanner ────────────────────────────────────────────────
if menu == "Fraud Scanner":
    st.title("🛡️ Sentinel: Context-Aware Fraud Engine")
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 Transaction Context")
        with st.form("fraud_input_form"):
            c_col1, c_col2 = st.columns(2)
            customer_id = c_col1.text_input(
                "Customer ID", value="CUST_88223",
                help="Simulate users to test velocity",
            )
            ip_addr = c_col2.text_input("IP Address", value="192.168.1.5")
            type_val = st.selectbox(
                "Transaction Type", ["CASH_OUT", "TRANSFER", "PAYMENT"],
            )
            amount = st.number_input("Amount ($)", value=5000.0, step=100.0)
            old_balance = st.number_input("Old Balance ($)", value=5000.0, step=100.0)
            new_balance = st.number_input("New Balance ($)", value=0.0, step=100.0)
            submit_button = st.form_submit_button("🛡️ Analyze Risk", type="primary")

    with col2:
        st.subheader("📊 Intelligence Report")
        if submit_button:
            payload = {
                "customer_id": customer_id,
                "ip_address": ip_addr,
                "type": type_val,
                "amount": amount,
                "oldbalanceOrg": old_balance,
                "newbalanceOrig": new_balance,
            }
            try:
                response = requests.post(
                    f"{API_URL}/v1/predict", json=payload, headers=HEADERS, timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    action = data["action"]
                    color = (
                        "green" if action == "ALLOW"
                        else "orange" if action == "CHALLENGE"
                        else "red"
                    )
                    st.markdown(
                        f"""
                        <div style="padding: 20px; background-color: rgba(255,255,255,0.05);
                                    border-left: 5px solid {color}; border-radius: 5px;">
                            <h2 style="color:{color}; margin:0;">{action}</h2>
                            <p style="margin:0;">Risk Level: <b>{data['risk_score']}</b></p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    v_col1, v_col2 = st.columns(2)
                    v_col1.metric("Velocity (1h)", f"{data['velocity_1h']} txns")
                    v_col1.metric("Confidence", f"{data['confidence']:.2%}")
                    v_col1.metric("Threshold", f"{data['decision_threshold']:.4f}")

                    v_col2.write("**Risk Signals:**")
                    if data["reasons"]:
                        for r in data["reasons"]:
                            v_col2.caption(f"🚩 {r}")
                    else:
                        v_col2.caption("✅ None")

                    v_col2.write(f"**Model:** {data['model_version']}")
                    v_col2.write(f"**A/B Variant:** {data['ab_variant']}")

                elif response.status_code == 403:
                    st.error("⛔ Access Denied: Invalid API Key.")
                else:
                    st.error(f"Server Error ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection Error: Could not reach the Backend.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ── 2. Live Feed ────────────────────────────────────────────────────
elif menu == "Live Feed":
    try:
        from pages.live_feed import show_live_feed
        show_live_feed()
    except ImportError:
        st.title("📡 Live Fraud Alerts")
        st.info("WebSocket live feed requires the `websocket-client` package.")
        st.caption("Run: pip install websocket-client")

# ── 3. Transaction History ──────────────────────────────────────────
elif menu == "Transaction History":
    st.title("📜 Transaction Audit Log")
    if st.button("🔄 Refresh Log"):
        try:
            response = requests.get(
                f"{API_URL}/v1/history", headers=HEADERS, timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Download CSV", csv, "audit.csv", "text/csv")
                else:
                    st.info("No transactions found yet.")
            else:
                st.error("Failed to fetch history.")
        except Exception as e:
            st.error(f"Connection Error: {e}")

# ── 4. Drift Monitor ───────────────────────────────────────────────
elif menu == "Drift Monitor":
    try:
        from pages.drift_monitor import show_drift
        show_drift()
    except ImportError:
        st.title("📉 Drift Monitor")
        st.error("drift_monitor.py missing")

# ── 5. System Health ───────────────────────────────────────────────
elif menu == "System Health":
    try:
        from pages.system_health import show_health
        show_health()
    except ImportError:
        st.title("🏥 System Health")
        st.error("system_health.py missing")

# ── Footer ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Sentinel AI v2.0 | Engineered by Chirag Sharma")
