from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def check_drift_result(**kwargs):
    """
    Queries the database for the LATEST drift report.
    Returns 'retrain_model_task' if drift=True, else 'no_drift_detected_task'.
    """
    try:
        # 1. Connect to the Database using Airflow's built-in Hook
        # Note: We assume a connection named 'postgres_default' exists (standard in Airflow)
        # If connection fails, we fall back to psycopg2 manually using env vars
        import psycopg2
        
        conn = psycopg2.connect(
            host="postgres",
            database="mlflow_db",
            user="mlflow_user",
            password="mlflow_password",
            port="5432"
        )
        cursor = conn.cursor()
        
        # 2. Get the most recent drift report
        print("Querying database for latest drift status...")
        cursor.execute("SELECT drift_detected FROM drift_reports ORDER BY created_at DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        # 3. Decision Logic
        if result:
            drift_detected = result[0] # This will be True or False boolean from DB
            print(f"Latest Drift Status from DB: {drift_detected}")
        else:
            print("No drift reports found in DB. Assuming healthy.")
            drift_detected = False

        if drift_detected:
            return 'retrain_model_task'
        else:
            return 'no_drift_detected_task'

    except Exception as e:
        print(f"Error connecting to DB: {e}")
        # Default safety mechanism: If DB fails, don't retrain blindly.
        return 'no_drift_detected_task'

with DAG(
    'drift_check_daily',
    default_args=default_args,
    description='Runs drift monitoring and triggers retraining based on DB results',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['mlops', 'monitoring', 'automation'],
) as dag:

    # TASK 1: Run the Drift Monitor
    check_drift_task = BashOperator(
        task_id='check_data_drift',
        bash_command='python /opt/airflow/src/drift_monitor.py',
        env={
            **os.environ,
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "mlflow_db",
            "POSTGRES_USER": "mlflow_user",
            "POSTGRES_PASSWORD": "mlflow_password",
            "PYTHONPATH": "/opt/airflow:/home/airflow/.local/lib/python3.10/site-packages" 
        }
    )

    # TASK 2: The Decision Maker (Reading from DB)
    branch_task = BranchPythonOperator(
        task_id='decide_next_step',
        python_callable=check_drift_result,
        provide_context=True
    )

    # TASK 3 (Path A): Retrain Model
    retrain_task = BashOperator(
        task_id='retrain_model_task',
        bash_command='python /opt/airflow/src/train.py',
        env={
            **os.environ,
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "mlflow_db",
            "POSTGRES_USER": "mlflow_user",
            "POSTGRES_PASSWORD": "mlflow_password",
            "PYTHONPATH": "/opt/airflow:/home/airflow/.local/lib/python3.10/site-packages" 
        }
    )

    # TASK 4 (Path B): Do Nothing
    no_drift_task = DummyOperator(
        task_id='no_drift_detected_task'
    )

    check_drift_task >> branch_task
    branch_task >> [retrain_task, no_drift_task]
    