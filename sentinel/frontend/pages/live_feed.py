"""
Live Feed page — WebSocket-connected real-time fraud alert stream.
"""

import json
import os
import time

import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
WS_URL = API_URL.replace("http", "ws")


def show_live_feed():
    """Render the live fraud alert feed."""
    st.title("📡 Live Fraud Alerts")
    st.caption("Real-time feed of BLOCK decisions via WebSocket")

    # Display instructions for connecting
    st.info(
        f"WebSocket endpoint: `{WS_URL}/ws/alerts`\n\n"
        "BLOCK decisions are broadcast to all connected clients in real-time."
    )

    # Polling-based alert display (simpler than raw WebSocket in Streamlit)
    st.subheader("Recent Alerts")
    alert_container = st.empty()

    if st.button("🔄 Refresh Alerts"):
        try:
            import requests
            API_KEY = os.getenv("API_KEY", "")
            response = requests.get(
                f"{API_URL}/v1/history?limit=20",
                headers={"x-api-key": API_KEY},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                blocked = [t for t in data if t.get("action") == "BLOCK"]
                if blocked:
                    import pandas as pd
                    df = pd.DataFrame(blocked)
                    cols_to_show = [
                        "transaction_id", "customer_id", "amount",
                        "risk_score", "timestamp",
                    ]
                    available_cols = [c for c in cols_to_show if c in df.columns]
                    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
                else:
                    st.success("No BLOCK decisions in recent history.")
            else:
                st.error(f"Failed to fetch alerts: {response.status_code}")
        except Exception as e:
            st.error(f"Connection Error: {e}")
