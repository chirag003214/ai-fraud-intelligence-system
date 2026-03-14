"""
Drift Monitor page — calls real /v1/drift endpoint.

Replaces the original simulated drift data with real PSI computation.
"""

import os

import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "")
HEADERS = {"x-api-key": API_KEY}


def show_drift():
    """Render the drift monitoring dashboard."""
    st.title("📉 Feature Drift Monitor")
    st.caption("Real PSI (Population Stability Index) computed from live transactions")

    if st.button("🔄 Compute Drift Report"):
        try:
            import requests
            response = requests.get(
                f"{API_URL}/v1/drift", headers=HEADERS, timeout=30,
            )
            if response.status_code == 200:
                data = response.json()

                # Status banner
                status = data.get("status", "unknown")
                if status == "stable":
                    st.success(f"✅ Model is Stable — Max PSI: {data.get('max_psi', 0):.4f}")
                elif status == "drift_detected":
                    st.error(f"🔴 Drift Detected — Max PSI: {data.get('max_psi', 0):.4f}")
                elif status == "insufficient_data":
                    st.warning(
                        f"⚠️ Insufficient data — need at least "
                        f"{data.get('min_required', 100)} transactions"
                    )
                else:
                    st.info(f"Status: {status}")

                # Per-feature PSI table
                features = data.get("features", {})
                if features:
                    st.subheader("PSI by Feature")
                    df = pd.DataFrame([
                        {
                            "Feature": k,
                            "PSI": v,
                            "Status": (
                                "🟢 Stable" if v < 0.1
                                else "🟡 Warning" if v < 0.2
                                else "🔴 Drift"
                            ),
                        }
                        for k, v in features.items()
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)

                # Metadata
                st.caption(
                    f"Sample size: {data.get('sample_size', 'N/A')} | "
                    f"Computed at: {data.get('computed_at', 'N/A')}"
                )
            else:
                st.error(f"Server Error: {response.status_code}")
        except Exception as e:
            st.error(f"Connection Error: {e}")
    else:
        st.info("Click the button to compute a real drift report from live transaction data.")
