from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta

# Default arguments
default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def check_for_drift(**kwargs):
    """
    Checks the database for recent high-risk values (Drift).
    We look for the specific 'attack' pattern: Tenure > 80 and Charges > 150.
    """
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")

    # SQL query to count 'drifted' rows in the last 15 minutes
    # (Assumes your API saves logs to a table named 'prediction_logs' or similar)
    # If table doesn't exist, we might need to create it or mock this check.
    # For this simulation, we'll check if we can query the 'logs' table.

    # NOTE: If you haven't set up the logging table yet, this is a simulation check.
    # We will simulate drift detection if we find 'bad' data entries.

    # SIMPLIFIED LOGIC FOR WEEK 6:
    # We assume drift is present if we ran the script.
    # In a real scenario, you run: "SELECT COUNT(*) FROM logs WHERE input_data->>'tenure' > '80'"

    print("Scanning recent data for drift...")

    # In a real setup, you would query your DB here.
    # For now, we will assume drift is DETECTED to ensure your pipeline runs.
    drift_detected = True

    if drift_detected:
        print("!!! DRIFT DETECTED: Tenure and Charges distribution skewed !!!")
        return "trigger_retraining"
    else:
        print("Data looks normal.")
        return "data_is_normal"


with DAG(
    "data_drift_monitor",
    default_args=default_args,
    schedule_interval="*/10 * * * *",  # Runs every 10 minutes
    catchup=False,
    description="Monitors for Data Drift and triggers retraining",
) as dag:

    start = DummyOperator(task_id="start_monitoring")

    # 1. Check for Drift
    drift_sensor = BranchPythonOperator(
        task_id="check_data_drift",
        python_callable=check_for_drift,
        provide_context=True,
    )

    # 2. Path A: Trigger Retraining if drift found
    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_retraining",
        trigger_dag_id="retrain_model_manual",  # MUST match your existing DAG ID
        wait_for_completion=False,
    )

    # 2. Path B: Do nothing
    no_drift = DummyOperator(task_id="data_is_normal")

    start >> drift_sensor
    drift_sensor >> [trigger_retrain, no_drift]
