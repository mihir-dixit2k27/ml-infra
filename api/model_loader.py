#!/usr/bin/env python3
"""
Model loader for API usage - loads the latest MLflow model
"""

import os
import mlflow
import mlflow.sklearn
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(
        self,
        model_name="telco-churn-champion",
        tracking_uri="http://mlflow-ui:5000",
        model_alias=None,
    ):
        """
        Initialize model loader

        Args:
            model_name: Name of the registered model in MLflow
            tracking_uri: MLflow tracking server URI
            model_alias: Model alias to use (e.g., 'production', 'staging'). If None, uses latest version
        """
        self.model_name = model_name
        self.tracking_uri = tracking_uri
        self.model_alias = model_alias
        self.model = None
        self.model_version = None

        # Set MLflow tracking URI
        mlflow.set_tracking_uri(tracking_uri)

    def load_latest_model(self):
        """
        Load the latest version of the registered model or model with specified alias

        Returns:
            Loaded MLflow model
        """
        try:
            if self.model_alias:
                # Try to use model alias (e.g., production, staging)
                try:
                    model_uri = f"models:/{self.model_name}@{self.model_alias}"
                    logger.info(
                        f"Loading model with alias '{self.model_alias}': {model_uri}"
                    )
                    self.model = mlflow.pyfunc.load_model(model_uri)
                except Exception as alias_error:
                    logger.warning(
                        f"Failed to load model with alias '{self.model_alias}': {alias_error}"
                    )
                    logger.info(
                        f"Falling back to latest version of model '{self.model_name}'"
                    )
                    # Fall back to latest version without alias
                    client = mlflow.MlflowClient()
                    latest_version = client.get_latest_versions(
                        name=self.model_name, stages=["None"]
                    )[0]
                    self.model_version = latest_version.version
                    model_uri = f"models:/{self.model_name}/{self.model_version}"
                    logger.info(f"Loading latest model version: {model_uri}")
                    self.model = mlflow.pyfunc.load_model(model_uri)
            else:
                # Get the latest version of the registered model
                client = mlflow.MlflowClient()
                latest_version = client.get_latest_versions(
                    name=self.model_name,
                    stages=["None"],  # Get the latest version regardless of stage
                )[0]

                self.model_version = latest_version.version
                model_uri = f"models:/{self.model_name}/{self.model_version}"
                logger.info(f"Loading latest model version: {model_uri}")
                # Load the model using pyfunc for better compatibility
                self.model = mlflow.pyfunc.load_model(model_uri)

            # Extract version info if not already set
            if not self.model_version:
                try:
                    client = mlflow.MlflowClient()
                    if self.model_alias:
                        # Get version info for aliased model
                        model_info = client.get_model_version_by_name(
                            self.model_name, self.model_alias
                        )
                        self.model_version = model_info.version
                    else:
                        latest_version = client.get_latest_versions(
                            self.model_name, stages=["None"]
                        )[0]
                        self.model_version = latest_version.version
                except Exception:
                    self.model_version = "unknown"

            logger.info(f"Successfully loaded model version {self.model_version}")
            return self.model

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def load_model_by_version(self, version):
        """
        Load a specific version of the registered model

        Args:
            version: Model version to load

        Returns:
            Loaded MLflow model
        """
        try:
            model_uri = f"models:/{self.model_name}/{version}"
            logger.info(f"Loading model: {model_uri}")

            self.model = mlflow.sklearn.load_model(model_uri)
            self.model_version = version

            logger.info(f"Successfully loaded model version {version}")
            return self.model

        except Exception as e:
            logger.error(f"Failed to load model version {version}: {e}")
            raise

    def load_model_from_run(self, run_id):
        """
        Load model directly from a specific MLflow run

        Args:
            run_id: MLflow run ID

        Returns:
            Loaded MLflow model
        """
        try:
            model_uri = f"runs:/{run_id}/model"
            logger.info(f"Loading model from run: {model_uri}")

            self.model = mlflow.sklearn.load_model(model_uri)
            self.model_version = run_id

            logger.info(f"Successfully loaded model from run {run_id}")
            return self.model

        except Exception as e:
            logger.error(f"Failed to load model from run {run_id}: {e}")
            raise

    def predict(self, data):
        """
        Make predictions using the loaded model

        Args:
            data: Input data for prediction

        Returns:
            Model predictions
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_latest_model() first.")

        return self.model.predict(data)

    def predict_proba(self, data):
        """
        Get prediction probabilities using the loaded model

        Args:
            data: Input data for prediction

        Returns:
            Model prediction probabilities
        """
        if self.model is None:
            raise ValueError("No model loaded. Call load_latest_model() first.")

        # PyFuncModel wraps sklearn models, need to get the underlying sklearn model
        try:
            # Try to get the raw sklearn model
            if hasattr(self.model, "get_raw_model"):
                sklearn_model = self.model.get_raw_model()
                return sklearn_model.predict_proba(data)
            # Fallback: try unwrap_python_model
            elif hasattr(self.model, "unwrap_python_model"):
                sklearn_model = self.model.unwrap_python_model()
                return sklearn_model.predict_proba(data)
            # Last resort: try direct call (won't work for PyFuncModel)
            else:
                return self.model.predict_proba(data)
        except Exception as e:
            raise ValueError(f"Could not get predict_proba from model: {e}")

    def get_model_info(self):
        """
        Get information about the loaded model

        Returns:
            Dictionary with model information
        """
        if self.model is None:
            return {"error": "No model loaded"}

        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": type(self.model).__name__,
            "is_loaded": True,
        }


# Convenience function for quick model loading
def load_latest_model(
    model_name="telco-churn-champion", tracking_uri="http://127.0.0.1:5000"
):
    """
    Quick function to load the latest model

    Args:
        model_name: Name of the registered model
        tracking_uri: MLflow tracking server URI

    Returns:
        Loaded MLflow model
    """
    loader = ModelLoader(model_name, tracking_uri)
    return loader.load_latest_model()


if __name__ == "__main__":
    # Example usage
    try:
        # Load the latest model
        loader = ModelLoader()
        model = loader.load_latest_model()

        print("Model loaded successfully!")
        print(f"Model info: {loader.get_model_info()}")

        # Example prediction (you would use your actual data)
        import pandas as pd
        import numpy as np

        # Create sample data for testing
        sample_data = pd.DataFrame(
            {
                "SeniorCitizen": [0],
                "tenure": [12],
                "MonthlyCharges": [70.0],
                "TotalCharges": [840.0],
                "gender": ["Male"],
                "Partner": ["No"],
                "Dependents": ["No"],
                "PhoneService": ["Yes"],
                "MultipleLines": ["No"],
                "InternetService": ["DSL"],
                "OnlineSecurity": ["No"],
                "OnlineBackup": ["No"],
                "DeviceProtection": ["No"],
                "TechSupport": ["No"],
                "StreamingTV": ["No"],
                "StreamingMovies": ["No"],
                "Contract": ["Month-to-month"],
                "PaperlessBilling": ["Yes"],
                "PaymentMethod": ["Electronic check"],
            }
        )

        # Make prediction
        prediction = loader.predict(sample_data)
        probability = loader.predict_proba(sample_data)

        print(f"Prediction: {prediction[0]}")
        print(f"Probability: {probability[0]}")

    except Exception as e:
        print(f"Error: {e}")
