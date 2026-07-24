"""
DAG: cdc_maintenance

Delta VACUUM (spark_apps/maintenence/vacuum.py) rimuove i file non più
referenziati dal log delle transazioni Delta oltre la retention di default
(7 giorni). Va fatto girare periodicamente ma NON ad ogni ora come la
pipeline batch: è un'operazione più pesante e non urgente — una volta a
settimana è la cadenza standard consigliata da Delta Lake per tabelle con
questo volume di scrittura. Per questo è un DAG separato, non un task in
più dentro cdc_batch_pipeline.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="cdc_maintenance",
    description="Delta Lake VACUUM settimanale su bronze/silver/gold",
    default_args=default_args,
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["cdc", "maintenance"],
) as dag:
    # spark-master è un servizio long-running (a differenza di dbt/great-
    # expectations): qui `docker exec` è corretto e coerente con
    # spark_apps/spark_bronze.bash e spark_silver.bash, che usano lo stesso
    # pattern per sottomettere job al master già attivo.
    vacuum = BashOperator(
        task_id="delta_vacuum",
        bash_command=(
            "docker exec spark-master /opt/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "/opt/spark/apps/maintenence/vacuum.py"
        ),
    )
