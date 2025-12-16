import mlflow
from mlflow.tracking import MlflowClient
import shutil
import os

client = MlflowClient()
model_name = "FraudGuard"
destination_folder = "fraud_model"

print(f"🔍 Searching for latest version of '{model_name}'...")

try:
    # 1. Get the Run ID of the latest model
    versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
    latest_version = versions[-1]
    run_id = latest_version.run_id
    print(f"✅ Found latest model in Run ID: {run_id}")

    # 2. Get the physical location of that Run's artifacts
    run = client.get_run(run_id)
    artifact_uri = run.info.artifact_uri  # e.g., file:///C:/Users/.../artifacts
    
    # Clean up the path for Windows
    if artifact_uri.startswith("file:///"):
        local_path = artifact_uri[8:]
    elif artifact_uri.startswith("file://"):
        local_path = artifact_uri[7:]
    else:
        local_path = artifact_uri
        
    # Remove leading slash on Windows (e.g. /C:/ -> C:/)
    if os.name == 'nt' and local_path.startswith('/'):
        local_path = local_path.lstrip('/')

    print(f"📍 Real Artifact Path: {local_path}")

    # 3. Find the model folder inside artifacts
    # (It is usually named "model", "FraudGuard", or is the only folder there)
    source_model_path = os.path.join(local_path, "model") # Standard default
    
    if not os.path.exists(source_model_path):
        source_model_path = os.path.join(local_path, model_name) # Try model name
    
    if not os.path.exists(source_model_path):
        # Fallback: Grab the first folder we see
        subdirs = [f.path for f in os.scandir(local_path) if f.is_dir()]
        if subdirs:
            source_model_path = subdirs[0]
        else:
            raise Exception("Could not find a model folder inside artifacts!")

    print(f"📂 Copying from: {source_model_path}")

    # 4. Copy to deployment folder
    if os.path.exists(destination_folder):
        shutil.rmtree(destination_folder)
        
    shutil.copytree(source_model_path, destination_folder)
    print(f"🚀 SUCCESS! Model saved to '{destination_folder}'")

except Exception as e:
    print(f"❌ Error: {e}")