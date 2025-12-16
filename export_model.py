import mlflow
from mlflow.tracking import MlflowClient
import shutil
import os
import urllib.parse

client = MlflowClient()
model_name = "FraudGuard"
destination_folder = "fraud_model"

print(f"🔍 Searching for latest version of '{model_name}'...")

try:
    # 1. Get the Run ID
    versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
    latest_version = versions[-1]
    run_id = latest_version.run_id
    print(f"✅ Found latest model in Run ID: {run_id}")

    # 2. Get the physical location
    run = client.get_run(run_id)
    artifact_uri = run.info.artifact_uri
    
    # --- 🛡️ ROBUST PATH CLEANING FOR WINDOWS 🛡️ ---
    # Parse the URI to remove "file:", "file://", or "file:///"
    parsed_uri = urllib.parse.urlparse(artifact_uri)
    local_path = urllib.parse.unquote(parsed_uri.path)

    # If parsing returned an empty path (common with "file:C:/..."), handle it manually
    if not local_path and artifact_uri.startswith("file:"):
        local_path = artifact_uri[5:] # Strip "file:"
    
    # Remove leading slash if it exists (e.g. "/C:/Users" -> "C:/Users")
    if os.name == 'nt' and local_path.startswith('/') and ':' in local_path:
        local_path = local_path.lstrip('/')

    print(f"📍 Real Artifact Path: {local_path}")

    # 3. Find the model folder
    # We look for ANY folder inside the artifacts directory
    if not os.path.exists(local_path):
        raise Exception(f"Path does not exist: {local_path}")

    subdirs = [f.path for f in os.scandir(local_path) if f.is_dir()]
    
    if not subdirs:
        # Maybe the artifacts *are* the model folder?
        source_model_path = local_path
    else:
        # Usually the first folder inside is the model (e.g., "model" or "FraudGuard")
        source_model_path = subdirs[0]

    print(f"📂 Copying from: {source_model_path}")

    # 4. Copy to deployment folder
    if os.path.exists(destination_folder):
        shutil.rmtree(destination_folder)
        
    shutil.copytree(source_model_path, destination_folder)
    print(f"🚀 SUCCESS! Model saved to '{destination_folder}'")

except Exception as e:
    print(f"❌ Error: {e}")