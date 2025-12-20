from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

# Define default arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define the DAG
with DAG(
    "retrain_model_manual",  # DAG ID
    default_args=default_args,
    description="Retrains the model and updates production alias",
    schedule_interval=None,  # No schedule yet (we trigger it manually or via the other DAG)
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=["mlops", "training"],
) as dag:

    # Task: Run the training script
    train_task = BashOperator(
        task_id="train_champion_model",
        bash_command="python /opt/airflow/src/train.py",
        env={
            **os.environ,
            # CRITICAL: Tell the script where MLflow is (inside the Docker network)
            "MLFLOW_TRACKING_URI": "http://mlflow-ui:5000",
            # Ensure python path includes both airflow and user-installed packages (like joblib)
            "PYTHONPATH": "/opt/airflow:/home/airflow/.local/lib/python3.10/site-packages",
        },
    )
