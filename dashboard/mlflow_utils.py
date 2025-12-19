import os
import pandas as pd
import mlflow
import streamlit as st
from mlflow.tracking import MlflowClient

def get_latest_model_version(model_name):
    """
    Finds the highest version number of a registered model in MLflow.
    Returns the version string (e.g., "10") or None.
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-ui:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()
    
    try:
        # Get all versions for this model name
        versions = client.search_model_versions(f"name='{model_name}'")
        
        # Sort them by version number (descending) so the highest is first
        versions.sort(key=lambda x: int(x.version), reverse=True)
        
        if versions:
            return versions[0].version  # Return the highest version string
            
    except Exception as e:
        print(f"Error finding model version: {e}")
        
    return None

def load_latest_model(model_name):
    """
    Loads the absolute latest version of the model from MLflow.
    Returns: (model_object, version_string)
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-ui:5000")
    mlflow.set_tracking_uri(tracking_uri)
    
    try:
        # 1. Find the latest version number programmatically
        latest_version = get_latest_model_version(model_name)
        
        if latest_version:
            model_uri = f"models:/{model_name}/{latest_version}"
            print(f"🔹 Attempting to load model version: {latest_version}")
            model = mlflow.pyfunc.load_model(model_uri)
            return model, latest_version
        else:
            # Fallback: Try loading 'Production' if no versions found
            print("⚠️ No specific versions found. Trying 'Production' tag.")
            model_uri = f"models:/{model_name}/Production"
            model = mlflow.pyfunc.load_model(model_uri)
            return model, "Production"

    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None, "Error"

def get_model_performance(experiment_name: str = "churn-prediction-experiment") -> pd.DataFrame:
    """
    Fetch metrics for all finished runs in the given MLflow experiment.
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-ui:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        return pd.DataFrame()

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["attributes.start_time ASC"],
    )

    if not runs:
        return pd.DataFrame()

    records = []
    for r in runs:
        metrics = r.data.metrics
        info = r.info
        records.append(
            {
                "run_id": info.run_id,
                "start_time": pd.to_datetime(info.start_time, unit="ms"),
                "accuracy": metrics.get("accuracy"),
                "f1_score": metrics.get("f1_score"),
                "auc": metrics.get("auc"),
                "model_version": r.data.tags.get("model_version") or r.data.tags.get("mlflow.runName"),
            }
        )

    return pd.DataFrame(records).sort_values("start_time")