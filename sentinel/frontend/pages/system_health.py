"""
System Health page — calls real /v1/health and /v1/metrics endpoints.

Replaces simulated metrics with real data from the API.
"""

import os

import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "")
HEADERS = {"x-api-key": API_KEY}


def show_health():
    """Render the system health dashboard."""
    st.title("🏥 System Health Monitor")
    st.caption("Live metrics from the Sentinel API")

    if st.button("🔄 Refresh Health"):
        try:
            import requests

            # Health endpoint
            response = requests.get(
                f"{API_URL}/v1/health", headers=HEADERS, timeout=10,
            )
            if response.status_code == 200:
                data = response.json()

                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Status",
                    data.get("status", "unknown").upper(),
                )
                col2.metric(
                    "Uptime",
                    f"{data.get('uptime_seconds', 0):.0f}s",
                )
                col3.metric(
                    "Environment",
                    data.get("environment", "unknown"),
                )

                st.subheader("Service Status")
                services = {
                    "Database": data.get("database_connected", False),
                    "Redis": data.get("redis_connected", False),
                    "ML Model": data.get("model_loaded", False),
                }
                for svc, ok in services.items():
                    icon = "🟢" if ok else "🔴"
                    st.write(f"{icon} **{svc}**: {'Online' if ok else 'Offline'}")

                st.caption(f"API Version: {data.get('version', 'N/A')}")
            else:
                st.error(f"Health check failed: {response.status_code}")

            # Prometheus metrics (raw text)
            st.subheader("📊 Raw Prometheus Metrics")
            metrics_response = requests.get(
                f"{API_URL}/v1/metrics", timeout=10,
            )
            if metrics_response.status_code == 200:
                st.code(metrics_response.text[:2000], language="text")
            else:
                st.warning("Metrics endpoint not available.")

        except Exception as e:
            st.error(f"Connection Error: {e}")
    else:
        st.info("Click the button to fetch real system health data.")
