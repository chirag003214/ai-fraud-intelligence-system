import pandas as pd
import xgboost as xgb
import mlflow
import mlflow.sklearn  # <--- CHANGED THIS
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

# 1. Load Data
print("⏳ Loading dataset...")
df = pd.read_csv("data/PS_20174392719_1491204439457_log.csv")

# 2. Preprocessing & Feature Engineering
print("🛠️ Preprocessing...")
df = df[df['type'].isin(['CASH_OUT', 'TRANSFER'])]
df['type'] = df['type'].map({'CASH_OUT': 0, 'TRANSFER': 1})

df['errorBalanceOrg'] = df.newbalanceOrig + df.amount - df.oldbalanceOrg

X = df[['type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'errorBalanceOrg']]
y = df['isFraud']

# 3. Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train Model
print("🚀 Training XGBoost Model...")
mlflow.set_experiment("Fraud_Detection_System")

with mlflow.start_run():
    # Train
    model = xgb.XGBClassifier(scale_pos_weight=99, eval_metric='logloss')
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    f1 = f1_score(y_test, y_pred)
    print(f"✅ Model Trained! F1 Score: {f1:.4f}")
    
    # Log Metrics
    mlflow.log_metric("f1_score", f1)
    
    # 5. Register Model (USING SKLEARN METHOD TO FIX ERROR)
    print("💾 Saving Model...")
    mlflow.sklearn.log_model(
        sk_model=model,
        artifact_path="model",
        registered_model_name="FraudGuard"
    )
    print("✅ Model Registered as 'FraudGuard'. Ready for Backend.")