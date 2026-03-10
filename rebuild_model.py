import pandas as pd
import xgboost as xgb
import mlflow
import shutil
import os

# 1. Define Paths
MODEL_PATH = "fraud_model"

# 2. Clean up old model (Delete if exists)
if os.path.exists(MODEL_PATH):
    print(f"🧹 Deleting old {MODEL_PATH}...")
    shutil.rmtree(MODEL_PATH)

# 3. Generate Synthetic Training Data (Matches PaySim structure)
print("📊 Generating training data...")
# We create 1000 rows of dummy data to "teach" the model
data = pd.DataFrame({
    'type': [0, 1, 0, 1, 4] * 200,  # Mapped: CASH_OUT=0, TRANSFER=1, etc.
    'amount': [100.0, 5000.0, 20.0, 100000.0, 50.0] * 200,
    'oldbalanceOrg': [1000.0, 5000.0, 500.0, 100000.0, 100.0] * 200,
    'newbalanceOrig': [900.0, 0.0, 480.0, 0.0, 50.0] * 200,
    'errorBalanceOrg': [0.0, 0.0, 0.0, 0.0, 0.0] * 200, # Engineered feature
    'isFraud': [0, 1, 0, 1, 0] * 200
})

X = data.drop(columns=['isFraud'])
y = data['isFraud']

# 4. Train XGBoost Model
print("🧠 Training XGBoost Model...")
model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=50,
    max_depth=3
)
model.fit(X, y)

# 5. Save Model using MLflow (Format required by your Backend)
print(f"💾 Saving model to '{MODEL_PATH}'...")
mlflow.xgboost.save_model(model, MODEL_PATH)

print("✅ SUCCESS! Model rebuilt. You MUST restart your backend now.")