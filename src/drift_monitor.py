# src/drift_monitor.py
"""
Drift monitoring script for detecting data drift in production predictions
"""

import pandas as pd
import json
import psycopg2
import os
import time
from pathlib import Path
import sys
from sqlalchemy import create_engine
from datetime import datetime
import logging

# Statistical tests (scipy)
from scipy.stats import (
    ks_2samp,
    chisquare,
)  # noqa: F401 (chisquare reserved for future categorical tests)


# --- Resilient DB Connection ---
def get_db_connection(retries=5, delay=3):
    """Establishes a connection to PostgreSQL running on the host via mapped port."""
    db_name = os.getenv("POSTGRES_DB", "mlflow_db")
    db_user = os.getenv("POSTGRES_USER", "mlflow_user")
    db_pass = os.getenv("POSTGRES_PASSWORD", "mlflow_password")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5433")

    for i in range(retries):
        try:
            conn = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_pass,
                host=db_host,
                port=db_port,
            )
            print("--- Database connection successful (via host port) ---")
            return conn
        except psycopg2.OperationalError as e:
            print(f"DB connection failed (attempt {i+1}/{retries}). Error: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print("--- Max DB connection retries reached. Giving up. ---")
                raise


def get_sqlalchemy_engine():
    """Creates a SQLAlchemy engine for connecting to PostgreSQL."""
    db_name = os.getenv("POSTGRES_DB", "mlflow_db")
    db_user = os.getenv("POSTGRES_USER", "mlflow_user")
    db_pass = os.getenv("POSTGRES_PASSWORD", "mlflow_password")
    db_host = os.getenv(
        "POSTGRES_HOST", "localhost"
    )  # Default to localhost only if env var is missing
    db_port = os.getenv(
        "POSTGRES_PORT", "5433"
    )  # Default to 5433 only if env var is missing
    db_uri = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    try:
        engine = create_engine(db_uri)
        # Test connection
        connection = engine.connect()
        connection.close()
        print("--- SQLAlchemy engine created successfully ---")
        return engine
    except Exception as e:
        print(f"Failed to create SQLAlchemy engine: {e}")
        raise


# --- Data Fetching Functions ---
def fetch_recent_predictions_sqlalchemy(engine, limit=1000):
    """Fetches the latest prediction logs into a pandas DataFrame using SQLAlchemy."""
    try:
        query = f"""
        SELECT 
            gender, seniorcitizen, partner, dependents, tenure, phoneservice, 
            multiplelines, internetservice, onlinesecurity, onlinebackup, 
            deviceprotection, techsupport, streamingtv, streamingmovies, contract, 
            paperlessbilling, paymentmethod, monthlycharges, totalcharges
        FROM prediction_logs 
        ORDER BY timestamp DESC 
        LIMIT {limit}
        """
        df = pd.read_sql(query, engine)
        print(f"--- Fetched {len(df)} recent predictions ---")
        return df
    except Exception as e:
        print(f"Error fetching predictions: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


def fetch_recent_predictions_psycopg2(conn, limit=1000):
    """Fetches the latest prediction logs into a pandas DataFrame using psycopg2."""
    cursor = None
    try:
        cursor = conn.cursor()
        query = f"""
        SELECT 
            gender, seniorcitizen, partner, dependents, tenure, phoneservice, 
            multiplelines, internetservice, onlinesecurity, onlinebackup, 
            deviceprotection, techsupport, streamingtv, streamingmovies, contract, 
            paperlessbilling, paymentmethod, monthlycharges, totalcharges
        FROM prediction_logs 
        ORDER BY timestamp DESC 
        LIMIT {limit}
        """
        cursor.execute(query)
        # Fetch column names
        colnames = [desc[0] for desc in cursor.description]
        # Fetch all rows
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=colnames)
        print(f"--- Fetched {len(df)} recent predictions ---")
        return df
    except Exception as e:
        print(f"Error fetching predictions: {e}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.close()


# --- Baseline Stats Loading ---
# Define path relative to this script's location
SCRIPT_DIR = Path(__file__).parent
STATS_FILE_PATH = SCRIPT_DIR.parent / "data" / "processed" / "train_stats_v1.0.json"
PROJECT_ROOT = SCRIPT_DIR.parent

# --- Drift thresholds ---
Z_SCORE_THRESHOLD = float(
    os.getenv("DRIFT_Z_SCORE_THRESHOLD", "3.0")
)  # Configurable via env var
KS_P_VALUE_THRESHOLD = 0.05
# PSI_THRESHOLD = 0.1  # reserved for future use
# CHI2_P_VALUE_THRESHOLD = 0.05  # reserved for future use

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def load_baseline_stats(path=STATS_FILE_PATH):
    """Loads the baseline training data statistics from the JSON file."""
    try:
        with open(path, "r") as f:
            baseline_stats = json.load(f)
        print(f"--- Baseline stats loaded successfully from {path} ---")

        # Enhanced validation - check for numeric stats
        has_numeric_stats = any(
            key in baseline_stats
            for key in ["numeric_stats", "SeniorCitizen", "tenure"]
        )
        if not has_numeric_stats:
            print(
                "Warning: Baseline stats file might be missing expected numeric statistics keys."
            )
            print(f"Available keys: {list(baseline_stats.keys())[:10]}")
        else:
            print(
                f"--- Found {len([k for k in baseline_stats.keys() if k not in ['timestamp', 'training_rows', 'data_hash']])} feature statistics ---"
            )
        # Build helper maps for means/stds using lowercase keys to align with DB column names
        feature_means = {}
        feature_stds = {}
        for k, v in baseline_stats.items():
            if isinstance(v, dict) and "mean" in v:
                feature_means[k.lower()] = v.get("mean")
                feature_stds[k.lower()] = v.get("std", 0)
        baseline_stats["feature_means"] = feature_means
        baseline_stats["feature_stds"] = feature_stds
        return baseline_stats
    except FileNotFoundError:
        print(f"Error: Baseline stats file not found at {path}")
        print(f"Checked path: {path.resolve()}")
        sys.exit(1)  # Exit if baseline is missing
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading baseline stats: {e}")
        sys.exit(1)


# --- Drift Detection ---
def check_drift(recent_df, baseline_stats, numeric_features, categorical_features):
    """Compares recent data distribution against baseline stats for drift."""
    drift_report = {"drift_detected": False, "drifted_features": []}

    # Numeric drift via mean shift (z-score)
    print("\n--- Checking Numeric Drift ---")
    baseline_means = baseline_stats.get("feature_means", {})
    baseline_stds = baseline_stats.get("feature_stds", {})

    for feature in numeric_features:
        if feature in recent_df.columns and feature in baseline_means:
            try:
                recent_mean = recent_df[feature].dropna().mean()
                baseline_mean = baseline_means.get(feature, None)
                baseline_std = baseline_stds.get(feature, 1)  # avoid division by zero
                if baseline_mean is not None:
                    z_score = (
                        abs(recent_mean - baseline_mean) / baseline_std
                        if baseline_std and baseline_std > 0
                        else 0
                    )
                    print(
                        f"Feature '{feature}': Recent Mean={recent_mean:.4f}, Baseline Mean={baseline_mean:.4f}, Z-score={z_score:.2f}"
                    )
                    if z_score > Z_SCORE_THRESHOLD:
                        print(
                            f"  -> DRIFT DETECTED (Z-score {z_score:.2f} > {Z_SCORE_THRESHOLD})"
                        )
                        drift_report["drift_detected"] = True
                        drift_report["drifted_features"].append(
                            f"{feature} (mean shift, z={z_score:.2f})"
                        )
                # Placeholder for KS-test (requires careful baseline distribution handling)
                # ks_stat, p_value = ks_2samp(recent_df[feature].dropna(), simulated_baseline)
                # if p_value < KS_P_VALUE_THRESHOLD:
                #     drift_report["drift_detected"] = True
                #     drift_report["drifted_features"].append(f"{feature} (distribution shift)")
            except Exception as e:
                print(f"Error checking drift for numeric feature '{feature}': {e}")
        else:
            print(
                f"Skipping numeric feature '{feature}': Not found in recent data or baseline stats."
            )

    # Categorical drift placeholder
    print("\n--- Checking Categorical Drift (Placeholder) ---")
    baseline_cats = baseline_stats.get("categorical_distributions", {})
    for feature in categorical_features:
        if feature in recent_df.columns and feature in baseline_cats:
            print(f"Feature '{feature}': Checking distribution... (not implemented)")
            # TODO: Implement chi-squared or PSI in future
            pass
        else:
            print(f"Skipping categorical feature '{feature}': Not found.")

    drift_report["drifted_features"] = list(set(drift_report["drifted_features"]))
    return drift_report


# --- Drift Reporting to DB ---
def ensure_drift_reports_table(conn):
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS drift_reports (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                drift_detected BOOLEAN NOT NULL,
                drifted_features TEXT,
                checked_rows INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error ensuring drift_reports table: {e}")
    finally:
        if cursor:
            cursor.close()


def log_drift_report_to_db(drift_result, checked_rows, conn):
    """Logs the drift check results to the drift_reports table."""
    cursor = None
    try:
        ensure_drift_reports_table(conn)
        cursor = conn.cursor()
        query = """
        INSERT INTO drift_reports (drift_detected, drifted_features, checked_rows) 
        VALUES (%s, %s, %s)
        """
        # Use JSON format for better querying (fallback to comma-separated for compatibility)
        drifted_features = drift_result.get("drifted_features", [])
        if drifted_features:
            drifted_features_str = (
                json.dumps(drifted_features)
                if len(drifted_features) > 1
                else drifted_features[0]
            )
        else:
            drifted_features_str = ""
        log_data = (
            drift_result.get("drift_detected", False),
            drifted_features_str,
            checked_rows,
        )
        cursor.execute(query, log_data)
        conn.commit()
        print("--- Drift report logged to database successfully. ---")
    except Exception as e:
        print(f"Error logging drift report to database: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()


# --- Main Execution Block ---
if __name__ == "__main__":
    print("=" * 60)
    print("--- Running Drift Monitor Script ---")
    print("=" * 60)

    # Define feature lists (DB columns are lowercase)
    numeric_features = ["seniorcitizen", "tenure", "monthlycharges", "totalcharges"]
    categorical_features = [
        "gender",
        "partner",
        "dependents",
        "phoneservice",
        "multiplelines",
        "internetservice",
        "onlinesecurity",
        "onlinebackup",
        "deviceprotection",
        "techsupport",
        "streamingtv",
        "streamingmovies",
        "contract",
        "paperlessbilling",
        "paymentmethod",
    ]

    # Load baseline stats
    baseline_stats = load_baseline_stats()

    # Fetch recent predictions
    engine = None
    recent_predictions_df = pd.DataFrame()
    try:
        engine = get_sqlalchemy_engine()
        recent_predictions_df = fetch_recent_predictions_sqlalchemy(engine, limit=500)
    except Exception as e:
        print(f"\n❌ SQLAlchemy execution failed: {e}")

    if not recent_predictions_df.empty:
        print(f"\nShape of fetched data: {recent_predictions_df.shape}")

        # Perform drift check
        drift_result = check_drift(
            recent_predictions_df,
            baseline_stats,
            numeric_features,
            categorical_features,
        )
        print(f"\nDrift Check Result: {drift_result}")

        # Log report to DB (use raw connection from engine if available)
        db_conn_for_log = None
        try:
            if engine:
                db_conn_for_log = engine.raw_connection()
            else:
                db_conn_for_log = get_db_connection()
            if db_conn_for_log:
                log_drift_report_to_db(
                    drift_result, len(recent_predictions_df), db_conn_for_log
                )
        finally:
            if db_conn_for_log:
                try:
                    db_conn_for_log.close()
                except Exception:
                    pass

        # Alerting via flag file
        drift_flag_file = PROJECT_ROOT / "drift_detected.flag"
        if drift_result.get("drift_detected"):
            print("!" * 27)
            print("!!! DRIFT DETECTED !!!")
            print(f"!!! Drifted features: {drift_result.get('drifted_features', [])}")
            print("!" * 27)
            # Write flag file with timestamp and drifted features info
            flag_content = {
                "timestamp": datetime.now().isoformat(),
                "drifted_features": drift_result.get("drifted_features", []),
                "checked_rows": len(recent_predictions_df),
            }
            with open(drift_flag_file, "w") as f:
                f.write(json.dumps(flag_content, indent=2))
            print(f"--- Created drift flag file: {drift_flag_file} ---")
        else:
            print("\n--- No significant drift detected. ---")
            if drift_flag_file.exists():
                os.remove(drift_flag_file)
                print("--- Removed existing drift flag file. ---")
    else:
        print(
            "\nNo recent predictions found or error fetching data. Skipping drift check."
        )

    # Cleanup engine
    if engine:
        engine.dispose()
        print("--- SQLAlchemy engine disposed ---")

    print("\n--- Drift Monitor Script Finished ---")
