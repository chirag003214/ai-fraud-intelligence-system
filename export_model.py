import mlflow
from mlflow.tracking import MlflowClient
import shutil
import os

# 1. Connect to local MLflow
client = MlflowClient()
model_name = "FraudGuard"

print(f"🔍 Searching for latest version of '{model_name}'...")

# 2. Get the location of the latest model
try:
    latest_versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
    latest_version = latest_versions[-1] # Get the most recent one
    source_path = latest_version.source
except Exception as e:
    print(f"❌ Error: Could not find model in registry. {e}")
    exit()

# 3. Clean up the path (Convert URI to Windows Path)
local_path = source_path
if source_path.startswith("file:///"):
    local_path = source_path[8:] # Remove file:///
elif source_path.startswith("file://"):
    local_path = source_path[7:]

# Fix for Windows paths (e.g. /C:/Users -> C:/Users)
if ":" in local_path and local_path.startswith("/"):
    local_path = local_path.lstrip("/")

print(f"✅ Found source model at: {local_path}")

# 4. Copy to a deployment folder
destination = "fraud_model"

if os.path.exists(destination):
    print(f"⚠️ Removing old '{destination}' folder...")
    shutil.rmtree(destination)

print(f"📂 Copying to '{destination}'...")
shutil.copytree(local_path, destination)

print("SUCCESS! 🚀")
print(f"The model is now saved in the '{destination}' folder.")