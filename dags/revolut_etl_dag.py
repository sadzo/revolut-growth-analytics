# =====================================================================
# Airflow DAG: Daily ETL for Revolut Growth Analytics (Conceptual)
#
# Purpose:
# - Show how the ETL pipeline in this project *could* be scheduled
#   in a real production setup using Apache Airflow.
#
# What this DAG does conceptually:
# 1) (Optional) Generate synthetic banking data
# 2) Run the ETL pipeline to build warehouse tables:
#    - dim_users
#    - fct_funnel
#    - fct_transactions
#
# Notes:
# - This file is meant as a learning + architectural example.
# - It is NOT required to run this project locally.
# - To actually run this DAG, an Airflow instance must be configured
#   with the project code available on its PYTHONPATH.
# =====================================================================

from datetime import datetime, timedelta
from pathlib import Path
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

# ---------------------------------------------------------------------
# Make the project importable inside Airflow
# ---------------------------------------------------------------------
# We assume this file lives in: <project_root>/dags/revolut_etl_dag.py
# So the project root is one level above "dags".
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

# Now we can import the ETL functions from the project
from etl.generate_fake_data import main as generate_fake_data_main
from etl.etl_pipeline import run_etl


# ---------------------------------------------------------------------
# Default DAG configuration (owner, retries, etc.)
# ---------------------------------------------------------------------
default_args = {
    "owner": "sadzo",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


# ---------------------------------------------------------------------
# Define the DAG
# ---------------------------------------------------------------------
# In a real Airflow setup, this DAG:
# - would run once per day at 06:00
# - would generate fresh synthetic data (optional)
# - would then run the ETL pipeline to refresh the warehouse tables.
# ---------------------------------------------------------------------
with DAG(
    dag_id="revolut_growth_etl_daily",
    description="Daily ETL for the Revolut growth analytics demo project (concept).",
    default_args=default_args,
    schedule_interval="0 6 * * *",  # every day at 06:00
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["revolut", "growth-analytics", "etl", "demo"],
) as dag:

    # -------------------------------------------------------------
    # Task 1: Generate synthetic data (optional)
    # -------------------------------------------------------------
    generate_fake_data_task = PythonOperator(
        task_id="generate_fake_banking_data",
        python_callable=generate_fake_data_main,
    )

    # -------------------------------------------------------------
    # Task 2: Run the ETL pipeline
    # -------------------------------------------------------------
    run_etl_task = PythonOperator(
        task_id="run_etl_pipeline",
        python_callable=run_etl,
    )

    # -------------------------------------------------------------
    # Task dependencies (order of execution)
    # -------------------------------------------------------------
    # First: generate fake data
    # Then: run ETL on that data
    generate_fake_data_task >> run_etl_task
