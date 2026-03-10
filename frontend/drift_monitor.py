import streamlit as st
import numpy as np
import pandas as pd

def show_drift():
    st.caption("⚠️ Drift data shown is simulated for demonstration purposes.")
    st.title("📉 Feature Drift Monitor")

    st.subheader("PSI (Population Stability Index) by Feature")

    features = ["amount", "oldbalanceOrg", "newbalanceOrig", "errorBalanceOrg", "type"]
    psi_values = [round(np.random.uniform(0.01, 0.35), 3) for _ in features]

    drift_df = pd.DataFrame({"Feature": features, "PSI": psi_values})
    drift_df["Status"] = drift_df["PSI"].apply(
        lambda x: "🟢 Stable" if x < 0.1 else ("🟡 Warning" if x < 0.2 else "🔴 Drift Detected")
    )

    st.dataframe(drift_df, use_container_width=True, hide_index=True)

    st.subheader("PSI Trend (Simulated)")
    trend_data = pd.DataFrame(
        np.random.uniform(0.01, 0.3, size=(10, len(features))),
        columns=features
    )
    st.line_chart(trend_data)
