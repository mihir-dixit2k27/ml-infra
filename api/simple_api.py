#!/usr/bin/env python3
"""
Simple FastAPI server for the Telco Churn model
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import psycopg2
import time
import mlflow
from mlflow.tracking import MlflowClient
from model_loader import ModelLoader
import logging


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Telco Churn Prediction API", version="1.0.0")

# Get configuration from environment variables
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-ui:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "telco-churn-champion")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "production")  # Default to production alias
MODEL_URI = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"

# Global variables for model and version
CURRENT_MODEL_VERSION = "unknown"

# Initialize model loader with environment variables
model_loader = ModelLoader(
    model_name=MODEL_NAME, tracking_uri=MLFLOW_TRACKING_URI, model_alias=MODEL_ALIAS
)


# --- Resilient DB Connection ---
def get_db_connection(retries=5, delay=3):
    """Establishes a connection to PostgreSQL with retry logic."""
    for i in range(retries):
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB", "mlflow_db"),
                user=os.getenv("POSTGRES_USER", "mlflow_user"),
                password=os.getenv("POSTGRES_PASSWORD", "mlflow_password"),
                host=os.getenv("POSTGRES_HOST", "postgres"),  # Default to service name
                port=os.getenv("POSTGRES_PORT", "5432"),  # Default port
            )
            logger.info("--- Database connection successful ---")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(
                f"DB connection failed (attempt {i+1}/{retries}). Error: {e}"
            )
            if i < retries - 1:
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error("--- Max DB connection retries reached. Giving up. ---")
                raise  # Re-raise the exception after max retries


# Load the model at startup with retry logic
@app.on_event("startup")
async def load_model():
    """Loads model and fetches version on API startup with retry logic."""
    global CURRENT_MODEL_VERSION

    retries = 5
    delay = 5  # seconds between retries

    logger.info(
        f"--- Attempting to load model '{MODEL_NAME}' alias '{MODEL_ALIAS}' at startup ---"
    )
    logger.info(f"--- Using MLflow Tracking URI: {MLFLOW_TRACKING_URI} ---")
    logger.info(f"--- Will retry up to {retries} times with {delay}s delay ---")

    for attempt in range(retries):
        try:
            logger.info(
                f"--- [Attempt {attempt + 1}/{retries}] Connecting to MLflow and loading model... ---"
            )

            # Set MLflow tracking URI
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

            # Load model using model loader
            model_loader.load_latest_model()
            logger.info("--- Model loaded successfully from MLflow Registry. ---")

            # Fetch model version details using MlflowClient
            try:
                client = MlflowClient()

                # Try to get version by alias first
                try:
                    # Get model version with alias
                    model_version = client.get_model_version_by_name(
                        MODEL_NAME, MODEL_ALIAS
                    )
                    CURRENT_MODEL_VERSION = model_version.version
                    logger.info(
                        f"--- Fetched production model version: {CURRENT_MODEL_VERSION} ---"
                    )
                except Exception:
                    # Fallback: get latest version
                    latest_versions = client.get_latest_versions(MODEL_NAME, stages=[])
                    if latest_versions:
                        CURRENT_MODEL_VERSION = latest_versions[0].version
                        logger.info(
                            f"--- Fetched latest model version: {CURRENT_MODEL_VERSION} ---"
                        )
                    else:
                        CURRENT_MODEL_VERSION = "unknown"
                        logger.warning("--- Could not determine model version ---")

            except Exception as client_e:
                logger.warning(
                    f"Warning: Could not fetch model version details from MLflow: {client_e}"
                )
                CURRENT_MODEL_VERSION = "fetch_failed"

            # Success! Exit the retry loop
            logger.info("--- Model loading completed successfully at startup. ---")
            return

        except Exception as load_e:
            logger.warning(
                f"--- [Attempt {attempt + 1}/{retries}] Error loading model: {load_e} ---"
            )

            if attempt < retries - 1:
                logger.info(
                    f"--- Retrying in {delay} seconds... (MLflow server may still be starting) ---"
                )
                time.sleep(delay)
            else:
                # Max retries reached
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.error(
                    f"--- Max retries ({retries}) reached. Failed to load model at startup. ---"
                )
                logger.error(f"Error: {load_e}")
                logger.error(
                    f"Check if MLflow server ({MLFLOW_TRACKING_URI}) is running and model/alias exist."
                )
                logger.error("")
                logger.error("Common causes:")
                logger.error("  1. MLflow server not fully started (wait a bit longer)")
                logger.error("  2. Model artifacts missing from storage location")
                logger.error("  3. Model not properly registered in MLflow registry")
                logger.error("  4. Incorrect artifact path or volume mount")
                logger.error("")
                logger.error(
                    "API will start, but model needs to be loaded via lazy loading on first /predict call."
                )
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                CURRENT_MODEL_VERSION = "unknown"


# Pydantic models for request/response
class PredictionRequest(BaseModel):
    SeniorCitizen: int
    tenure: int
    MonthlyCharges: float
    TotalCharges: float
    gender: str
    Partner: str
    Dependents: str
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str


class PredictionResponse(BaseModel):
    prediction: int
    probability_no_churn: float
    probability_churn: float
    model_version: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    db_connected: bool = False
    current_model_version: str = "unknown"


class DBHealthResponse(BaseModel):
    status: str
    connected: bool
    message: str


# API endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    model_info = model_loader.get_model_info()

    # Check database connection
    db_connected = False
    try:
        conn = get_db_connection(retries=2, delay=1)
        conn.close()
        db_connected = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")

    return HealthResponse(
        status="healthy" if model_info.get("is_loaded", False) else "unhealthy",
        model_loaded=model_info.get("is_loaded", False),
        model_version=model_info.get("model_version", "unknown"),
        db_connected=db_connected,
        current_model_version=CURRENT_MODEL_VERSION,
    )


@app.get("/health/db", response_model=DBHealthResponse)
async def db_health_check():
    """Database health check endpoint"""
    try:
        conn = get_db_connection()
        # Test query
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return DBHealthResponse(
            status="healthy", connected=True, message="Database connection successful"
        )
    except Exception as e:
        return DBHealthResponse(
            status="unhealthy",
            connected=False,
            message=f"Database connection failed: {str(e)}",
        )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict customer churn based on input features and log to database
    """
    global CURRENT_MODEL_VERSION
    start_time = time.time()

    try:
        # Try to load model if not already loaded
        model_info = model_loader.get_model_info()
        if not model_info.get("is_loaded", False):
            logger.info("Model not loaded at startup, attempting to load now...")
            try:
                model_loader.load_latest_model()
                logger.info("--- Model loaded successfully via lazy loading. ---")

                # Try fetching version again if it failed at startup
                if CURRENT_MODEL_VERSION in ["unknown", "fetch_failed"]:
                    try:
                        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
                        client = MlflowClient()
                        model_version = client.get_model_version_by_name(
                            MODEL_NAME, MODEL_ALIAS
                        )
                        CURRENT_MODEL_VERSION = model_version.version
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Model not available. Please try again later.",
                )

        # Convert request to DataFrame
        data = pd.DataFrame([request.dict()])

        # Make prediction
        prediction = model_loader.predict(data)[0]
        probabilities = model_loader.predict_proba(data)[0]

        prediction_value = int(prediction)
        probability_churn = (
            float(probabilities[1])
            if len(probabilities) > 1
            else float(probabilities[0])
        )

        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Prediction: {prediction_value} | Proba: {probability_churn:.4f} | Version: {CURRENT_MODEL_VERSION} | Latency: {latency_ms:.2f}ms"
        )

        # --- Database Logging ---
        conn = None
        cursor = None
        try:
            conn = get_db_connection(retries=2, delay=1)
            cursor = conn.cursor()

            # Construct parameterized query matching table schema (all lowercase)
            query = """
            INSERT INTO prediction_logs (
                model_version, prediction, gender, seniorcitizen, partner, dependents,
                tenure, phoneservice, multiplelines, internetservice, onlinesecurity, onlinebackup,
                deviceprotection, techsupport, streamingtv, streamingmovies, contract, paperlessbilling,
                paymentmethod, monthlycharges, totalcharges
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Create tuple of values in the correct order (matching table columns)
            log_data = (
                CURRENT_MODEL_VERSION,
                prediction_value,
                request.gender,
                request.SeniorCitizen,
                request.Partner,
                request.Dependents,
                request.tenure,
                request.PhoneService,
                request.MultipleLines,
                request.InternetService,
                request.OnlineSecurity,
                request.OnlineBackup,
                request.DeviceProtection,
                request.TechSupport,
                request.StreamingTV,
                request.StreamingMovies,
                request.Contract,
                request.PaperlessBilling,
                request.PaymentMethod,
                request.MonthlyCharges,
                request.TotalCharges,
            )

            cursor.execute(query, log_data)
            conn.commit()
            logger.info("--- Prediction logged to database successfully. ---")

        except Exception as db_e:
            logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.error(f"Error logging prediction to database: {db_e}")
            logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            if conn:
                conn.rollback()  # Rollback transaction on error
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        # --- End DB Logging ---

        return PredictionResponse(
            prediction=prediction_value,
            probability_no_churn=float(probabilities[0]),
            probability_churn=probability_churn,
            model_version=CURRENT_MODEL_VERSION,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model/info")
async def model_info():
    """Get information about the loaded model"""
    return model_loader.get_model_info()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Telco Churn Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "model_info": "/model/info",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
