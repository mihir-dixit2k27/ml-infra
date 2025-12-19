#!/usr/bin/env python3
"""
Script to fix model registration by re-registering from existing artifacts
"""

import mlflow
from mlflow.tracking import MlflowClient
import os
from pathlib import Path

# Set tracking URI
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

client = MlflowClient()
MODEL_NAME = "telco-churn-champion"

print("=" * 60)
print("Fixing Model Registration")
print("=" * 60)

# Find a model artifact that exists
artifact_path = Path("mlartifacts/200974736127882443/models/m-d5d939a649314dbaa3a2eb9163252ccc/artifacts")
if not artifact_path.exists():
    print(f"❌ Artifact path not found: {artifact_path}")
    exit(1)

print(f"✅ Found artifacts at: {artifact_path}")

# Check if model.pkl exists
model_pkl = artifact_path / "model.pkl"
if not model_pkl.exists():
    print(f"❌ Model file not found: {model_pkl}")
    exit(1)

print(f"✅ Found model file: {model_pkl}")

# Try to create a temporary run and log the model
print("\n📝 Creating a new run to register the model...")
try:
    # Create a new experiment or use default
    experiment = mlflow.get_experiment_by_name("telco-churn")
    if experiment is None:
        experiment_id = mlflow.create_experiment("telco-churn")
        print(f"✅ Created experiment: telco-churn (ID: {experiment_id})")
    else:
        experiment_id = experiment.experiment_id
        print(f"✅ Using existing experiment: telco-churn (ID: {experiment_id})")
    
    # Start a run and log the model
    with mlflow.start_run(experiment_id=experiment_id) as run:
        print(f"✅ Started run: {run.info.run_id}")
        
        # Log the model from the artifact directory
        mlflow.sklearn.log_model(
            sk_model=None,  # We'll load it from the pickle file
            artifact_path="model",
            registered_model_name=MODEL_NAME
        )
        
        # Actually, let's copy the model files to the run's artifact directory
        import shutil
        run_artifact_dir = Path(f"mlruns/{experiment_id}/{run.info.run_id}/artifacts")
        run_artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from artifact_path to run_artifact_dir/model
        model_dir = run_artifact_dir / "model"
        model_dir.mkdir(exist_ok=True)
        
        for file in artifact_path.iterdir():
            if file.is_file():
                shutil.copy2(file, model_dir / file.name)
                print(f"  ✅ Copied: {file.name}")
        
        # Now log the model
        import pickle
        with open(model_pkl, 'rb') as f:
            model = pickle.load(f)
        
        mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
        print(f"✅ Logged model to run: {run.info.run_id}")
    
    # Get the latest version
    latest_versions = client.get_latest_versions(MODEL_NAME)
    if latest_versions:
        new_version = latest_versions[0].version
        print(f"✅ Registered as version: {new_version}")
        
        # Set as production
        client.set_registered_model_alias(MODEL_NAME, "production", new_version)
        print(f"✅ Set version {new_version} as production")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)

