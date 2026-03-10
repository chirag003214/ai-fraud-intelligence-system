import streamlit as st
import random
import time

def show_health():
    st.caption("⚠️ Metrics shown are simulated for demonstration purposes.")
    st.title("🏥 System Health Monitor")

    col1, col2, col3 = st.columns(3)
    col1.metric("API Latency", f"{random.randint(30, 120)} ms")
    col2.metric("Model Load Time", f"{random.uniform(0.5, 2.0):.1f}s")
    col3.metric("Uptime", f"{random.randint(90, 100)}%")

    st.subheader("Request Volume (Last 24h)")
    chart_data = [random.randint(10, 100) for _ in range(24)]
    st.bar_chart(chart_data)

    st.subheader("Error Rate")
    st.metric("5xx Errors (1h)", f"{random.randint(0, 5)}")
