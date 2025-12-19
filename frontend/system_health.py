import streamlit as st
import time
import random

def show_health():
    st.subheader("🏥 System Health Monitor")
    
    # Simulate Real-time Metrics
    col1, col2, col3 = st.columns(3)
    
    latency = random.randint(80, 150)
    cpu_usage = random.randint(20, 45)
    
    col1.metric(label="API Latency", value=f"{latency}ms", delta="-12ms")
    col2.metric(label="CPU Usage", value=f"{cpu_usage}%", delta="Stable")
    col3.metric(label="Memory Usage", value="512MB", delta="Normal")
    
    st.markdown("### 📡 Active Microservices")
    st.code("""
    [ONLINE]  Auth Service (v2.1)
    [ONLINE]  Transaction API (v1.4)
    [ONLINE]  Llama-3 Inference Engine
    [ONLINE]  XGBoost Predictor
    """, language="bash")
    
    st.success("✅ All Critical Systems Operational")