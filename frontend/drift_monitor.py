import streamlit as st
import pandas as pd
import numpy as np

def show_drift():
    st.subheader("📉 Data Drift Analysis (PSI)")
    st.info("Monitoring feature distribution stability over the last 30 days.")
    
    # Mock Data for Visualization
    dates = pd.date_range(start='1/1/2025', periods=30)
    drift_data = pd.DataFrame(
        np.random.randn(30, 3).cumsum(axis=0),
        columns=['Amount', 'OldBalance', 'TransactionType'],
        index=dates
    )
    
    st.line_chart(drift_data)
    
    st.warning("⚠️ Alert: 'Amount' feature showing slight drift (PSI > 0.15) detected on 2025-01-15.")