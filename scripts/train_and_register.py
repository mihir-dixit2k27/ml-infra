#!/usr/bin/env python3
"""
Minimal training script to train and register model to MLflow
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent
# Try multiple possible data locations
possible_paths = [
    PROJECT_ROOT / "data" / "processed",
    Path("/app/data/processed"),
    Path("./data/processed"),
]
DATA_DIR = None
for path in possible_paths:
    if path.exists() and (path / "train_v1.0.csv").exists():
        DATA_DIR = path
        break
if DATA_DIR is None:
    raise FileNotFoundError("Could not find data directory")
TRAIN_CSV = DATA_DIR / "train_v1.0.csv"
VAL_CSV = DATA_DIR / "validation_v1.0.csv"

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
MLFLOW_EXPERIMENT = "Telco_Churn_Champion"
REGISTERED_MODEL_NAME = "telco-churn-champion"
MODEL_ALIAS = "production"

def prepare_target(df, target_col="Churn"):
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found")
    if df[target_col].dtype == object:
        df[target_col] = df[target_col].apply(lambda x: 1 if str(x).strip().lower() == 'yes' else 0)
    return df

def main():
    # Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    
    print(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"Experiment: {MLFLOW_EXPERIMENT}")
    
    # Load data
    train_df = pd.read_csv(TRAIN_CSV)
    val_df = pd.read_csv(VAL_CSV)
    train_df = prepare_target(train_df)
    val_df = prepare_target(val_df)
    
    # Split features and target
    TARGET = "Churn"
    y_train = train_df[TARGET]
    X_train = train_df.drop(columns=[TARGET])
    y_val = val_df[TARGET]
    X_val = val_df.drop(columns=[TARGET])
    
    # Build pipeline
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_features = X_train.select_dtypes(include=['object', 'category']).columns.tolist()
    
    numeric_transformer = Pipeline(steps=[("scaler", StandardScaler())])
    categorical_transformer = Pipeline(steps=[("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features)
        ],
        remainder="drop"
    )
    
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42))
    ])
    
    # Train
    print("Training model...")
    pipeline.fit(X_train, y_train)
    
    # Predict
    y_pred = pipeline.predict(X_val)
    y_prob = pipeline.predict_proba(X_val)[:, 1]
    
    # Metrics
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "f1_score": f1_score(y_val, y_pred),
        "auc": roc_auc_score(y_val, y_prob)
    }
    print(f"Metrics: {metrics}")
    
    # Log to MLflow and register
    with mlflow.start_run(run_name="Champion_v1.0_minimal") as run:
        # Log metrics
        mlflow.log_metrics(metrics)
        mlflow.log_param("random_seed", 42)
        
        # Log and register model
        signature = infer_signature(X_val, pipeline.predict(X_val))
        input_example = X_val.iloc[:1]
        
        print("Logging model to MLflow...")
        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="model",
            signature=signature,
            input_example=input_example
        )
        
        print(f"Model logged to: {model_info.model_uri}")
        
        # Register model
        print("Registering model...")
        model_version = mlflow.register_model(
            model_uri=model_info.model_uri,
            name=REGISTERED_MODEL_NAME
        )
        print(f"Model registered: version {model_version.version}")
        
        # Set alias
        client = mlflow.tracking.MlflowClient()
        client.set_registered_model_alias(
            name=REGISTERED_MODEL_NAME,
            alias=MODEL_ALIAS,
            version=str(model_version.version)
        )
        print(f"Alias '{MODEL_ALIAS}' set to version {model_version.version}")
        
        print(f"\n✅ Model successfully registered!")
        print(f"Run ID: {run.info.run_id}")
        print(f"Model: {REGISTERED_MODEL_NAME}@{MODEL_ALIAS}")
        print(f"Version: {model_version.version}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

