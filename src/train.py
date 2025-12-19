#!/usr/bin/env python3
"""
src/train.py

Reproducible training + MLflow logging for the Telco churn champion model.

Usage:
    python src/train.py

Assumptions:
- data/processed/train_v1.0.csv and data/processed/validation_v1.0.csv exist.
- MLflow server is reachable at MLFLOW_TRACKING_URI env var or default http://127.0.0.1:5000
"""

from pathlib import Path
import json
import os
import random
import subprocess
import sys
import hashlib
from datetime import datetime
import logging
import joblib
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, ConfusionMatrixDisplay

import matplotlib
matplotlib.use("Agg")  # for headless environments
import matplotlib.pyplot as plt

# -------------------------
# Configuration / Globals
# -------------------------
SEED = 42
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
TRAIN_CSV = DATA_DIR / "train_v1.0.csv"
VAL_CSV = DATA_DIR / "validation_v1.0.csv"
REQUIREMENTS_LOCK = PROJECT_ROOT / "requirements_lock.txt"

# MLflow config
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "Telco_Churn_Champion")
REGISTERED_MODEL_NAME = os.getenv("REGISTERED_MODEL_NAME", "telco-churn-champion")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# -------------------------
# Utilities
# -------------------------
def set_seed(seed: int = SEED):
    random.seed(seed)
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    logger.info(f"Random seed set to {seed}")


def load_data(train_path: Path = TRAIN_CSV, val_path: Path = VAL_CSV):
    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError(f"Train/Val CSVs not found at {train_path} and {val_path}")
    train = pd.read_csv(train_path)
    val = pd.read_csv(val_path)
    logger.info(f"Loaded train ({len(train)}) and val ({len(val)})")
    return train, val


def prepare_target(df: pd.DataFrame, target_col: str = "Churn"):
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in dataframe")
    # convert Yes/No to 1/0 if needed
    if df[target_col].dtype == object:
        df[target_col] = df[target_col].apply(lambda x: 1 if str(x).strip().lower() == 'yes' else 0)
    return df


def build_pipeline(X: pd.DataFrame, model_params: dict = None):
    numeric_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
    logger.info(f"Numeric features: {numeric_features}")
    logger.info(f"Categorical features: {categorical_features}")

    numeric_transformer = Pipeline(steps=[("scaler", StandardScaler())])
    categorical_transformer = Pipeline(steps=[("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features)
        ],
        remainder="drop"
    )

    if model_params is None:
        model_params = {"n_estimators": 100, "max_depth": 10, "random_state": SEED}

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(**model_params))
    ])
    return pipeline, numeric_features, categorical_features


def compute_metrics(y_true, y_pred, y_prob):
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    try:
        auc = roc_auc_score(y_true, y_prob)
    except Exception:
        auc = float("nan")
    return {"accuracy": float(acc), "f1_score": float(f1), "auc": float(auc)}


def save_confusion_matrix(model, X_val, y_val, out_path: Path):
    try:
        fig, ax = plt.subplots(figsize=(6, 5))
        ConfusionMatrixDisplay.from_estimator(model, X_val, y_val, ax=ax)
        plt.title("Confusion Matrix")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved confusion matrix to {out_path}")
        return out_path
    except Exception as e:
        logger.warning(f"Could not save confusion matrix: {e}")
        return None


def compute_data_stats(X_train: pd.DataFrame, numeric_features, categorical_features):
    stats = {}
    if len(numeric_features) > 0:
        numeric_stats = X_train[numeric_features].describe().to_dict()
        stats["numeric_stats"] = numeric_stats
    else:
        stats["numeric_stats"] = {}

    categorical_dists = {}
    for col in categorical_features:
        categorical_dists[col] = X_train[col].value_counts().to_dict()
    stats["categorical_distributions"] = categorical_dists

    stats["timestamp"] = datetime.utcnow().isoformat()
    stats["training_rows"] = len(X_train)

    # Data hash for audit: use pandas.util.hash_pandas_object
    try:
        hashed = pd.util.hash_pandas_object(X_train, index=True).values
        data_hash = hashlib.md5(hashed.tobytes()).hexdigest()
        stats["data_hash"] = data_hash
    except Exception as e:
        logger.warning(f"Failed to compute data hash: {e}")
        stats["data_hash"] = None

    return stats


def lock_requirements(lock_path: Path = REQUIREMENTS_LOCK):
    try:
        # Write pip freeze to a file
        with open(lock_path, "w") as f:
            subprocess.check_call([sys.executable, "-m", "pip", "freeze"], stdout=f)
        logger.info(f"Wrote requirements lock to {lock_path}")
        return lock_path
    except Exception as e:
        logger.warning(f"Failed to write requirements lock: {e}")
        return None


# -------------------------
# Main training & logging
# -------------------------
def train_and_log_model():
    set_seed(SEED)

    # MLflow setup
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    logger.info(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    logger.info(f"MLflow experiment: {MLFLOW_EXPERIMENT}")

    # Load data
    train_df, val_df = load_data()
    train_df = prepare_target(train_df, target_col="Churn")
    val_df = prepare_target(val_df, target_col="Churn")

    # Split X/y
    TARGET = "Churn"
    y_train = train_df[TARGET]
    X_train = train_df.drop(columns=[TARGET])
    y_val = val_df[TARGET]
    X_val = val_df.drop(columns=[TARGET])

    # Build pipeline
    pipeline, numeric_features, categorical_features = build_pipeline(X_train)

    model_params = pipeline.named_steps["classifier"].get_params()
    logger.info(f"Model params: {model_params}")

    run_info = {}

    with mlflow.start_run(run_name="Champion_v1.0") as run:
        try:
            # Train
            pipeline.fit(X_train, y_train)
            logger.info("Model training complete.")

            # Predict
            y_pred = pipeline.predict(X_val)
            try:
                y_prob = pipeline.predict_proba(X_val)[:, 1]
            except Exception:
                # If classifier doesn't support predict_proba
                y_prob = np.zeros(len(y_pred))

            # Metrics
            metrics = compute_metrics(y_val, y_pred, y_prob)
            logger.info(f"Metrics: {metrics}")

            # Log params & metrics
            mlflow.log_params({"n_estimators": model_params.get("n_estimators", None),
                               "max_depth": model_params.get("max_depth", None)})
            mlflow.log_param("random_seed", SEED)
            mlflow.log_metrics(metrics)

            # Confusion matrix artifact
            cm_path = PROJECT_ROOT / "artifacts" / "confusion_matrix.png"
            cm_saved = save_confusion_matrix(pipeline, X_val, y_val, cm_path)
            if cm_saved:
                mlflow.log_artifact(str(cm_saved.resolve()))

            # Log data snapshots for reproducibility
            mlflow.log_artifact(str(TRAIN_CSV.resolve()))
            mlflow.log_artifact(str(VAL_CSV.resolve()))

            # Data stats
            stats = compute_data_stats(X_train, numeric_features, categorical_features)
            stats_path = PROJECT_ROOT / "artifacts" / "train_stats_v1.0.json"
            stats_path.parent.mkdir(parents=True, exist_ok=True)
            with open(stats_path, "w") as f:
                json.dump(stats, f, indent=2)
            mlflow.log_artifact(str(stats_path.resolve()))

            # Environment info
            env_info = {
                "python_version": sys.version,
                "mlflow_version": mlflow.__version__,
            }
            # sklearn version
            try:
                import sklearn
                env_info["scikit_learn_version"] = sklearn.__version__
            except Exception:
                env_info["scikit_learn_version"] = "unknown"

            env_path = PROJECT_ROOT / "artifacts" / "environment_info.json"
            with open(env_path, "w") as f:
                json.dump(env_info, f, indent=2)
            mlflow.log_artifact(str(env_path.resolve()))

            # Requirements lock
            lock_path = lock_requirements()
            if lock_path:
                mlflow.log_artifact(str(lock_path.resolve()))

            # Log the model and register
            # --- Log the Model ---
            # ... (existing code for lock file logging) ...
            if lock_path:
                mlflow.log_artifact(str(lock_path.resolve()))

            # --- Log the Model ---
            logger.info("Logging the model artifact...")

            # === START OF NEW MANUAL SAVE CODE ===
            import joblib
            # Manually save model to local disk first
            local_model_path = PROJECT_ROOT / "model.pkl"
            print(f"Manually saving model to {local_model_path}...")
            joblib.dump(pipeline, local_model_path)
            
            # Log it as a generic artifact (this bypasses the sklearn flavor issues)
            mlflow.log_artifact(str(local_model_path), artifact_path="model")
            
            # Clean up local file
            os.remove(local_model_path)
            # === END OF NEW MANUAL SAVE CODE ===
            # ... (rest of your existing log_model code) ...
            logger.info("Logging the model artifact with signature and input example...")

            # Define the signature and input example
            signature = mlflow.models.infer_signature(X_val, pipeline.predict(X_val))
            input_example = X_val.iloc[:1] # Take the first row as an example

            # Step 1: Log the model files ONLY (no registration yet)
            # Include signature and input example here
            model_info = mlflow.sklearn.log_model(
                sk_model=pipeline,  # Use pipeline, not model
                artifact_path="model", 
                signature=signature, 
                input_example=input_example, 
                registered_model_name=None  # Explicitly disable registration here
            )
            
            print(f"Model artifact saved to path: {model_info.artifact_path}")

            # --- Register the Model Separately ---
            print("Registering the logged model...")
            # Step 2: Register the model using the artifact path from Step 1
            mlflow.register_model(
                model_uri=model_info.model_uri, # Use the URI of the just-logged artifact
                name=REGISTERED_MODEL_NAME      # Register it with this name
            )
            print("Model artifact logged and registration attempted.")


            logger.info("Model logged and attempted registration.")

            run_info["run_id"] = run.info.run_id
            run_info["metrics"] = metrics
            run_info["status"] = "SUCCESS"
            logger.info(f"MLflow run finished. Run ID: {run.info.run_id}")

        except Exception as e:
            logger.exception(f"Training failed: {e}")
            mlflow.log_param("failure_reason", str(e))
            run_info["status"] = "FAILED"
            raise

    return run_info


# -------------------------
# CLI entrypoint
# -------------------------
if __name__ == "__main__":
    try:
        info = train_and_log_model()
        logger.info(f"Finished run: {info}")
    except Exception as exc:
        logger.error(f"train_and_log_model() failed: {exc}")
        sys.exit(1)
