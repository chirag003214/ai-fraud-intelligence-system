import pandas as pd
from xgboost import XGBClassifier
import mlflow.sklearn
import os
import shutil

# --- CONFIGURATION ---
# We try to find your dataset automatically
data_folder = "data"
csv_file = None

print("🔍 Looking for dataset...")
if os.path.exists(data_folder):
    for f in os.listdir(data_folder):
        if f.endswith(".csv"):
            csv_file = os.path.join(data_folder, f)
            break

if not csv_file:
    print("❌ ERROR: Could not find a CSV file in the 'data' folder!")
    print("👉 Please make sure your dataset (PS_2017...) is inside the 'data' folder.")
    exit()

print(f"✅ Found data: {csv_file}")

# --- 1. LOAD & PREPROCESS ---
print("⏳ Loading data (this might take a moment)...")
df = pd.read_csv(csv_file)

# Filter only relevant transaction types (matching your Backend logic)
df = df.loc[(df.type == 'TRANSFER') | (df.type == 'CASH_OUT')]

# Feature Engineering (Must match Backend!)
df['errorBalanceOrg'] = df.newbalanceOrig + df.amount - df.oldbalanceOrg
df['type'] = df['type'].map({'CASH_OUT': 0, 'TRANSFER': 1})

# Select features
X = df[['type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'errorBalanceOrg']]
y = df['isFraud']

# --- 2. TRAIN ---
print("🧠 Training XGBoost Model...")
model = XGBClassifier()
model.fit(X, y)

# --- 3. SAVE FOR DEPLOYMENT ---
output_dir = "fraud_model"

# Clean up old folder if it exists
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

print(f"💾 Saving model to '{output_dir}'...")
mlflow.sklearn.save_model(model, output_dir)

print("🚀 SUCCESS! Model regenerated and saved.")
print("👉 You can now push to GitHub.")