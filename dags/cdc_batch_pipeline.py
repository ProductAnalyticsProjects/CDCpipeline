"""
DAG: cdc_batch_pipeline

Cosa orchestra e, soprattutto, cosa NON orchestra:

cdc_bronze.py e cdc_silver.py sono job di STREAMING continuo — finiscono in
`query.awaitTermination()` e non ritornano mai finché non li fermi. Sono
avviati una volta (a mano o via `docker exec spark-master spark-submit ...`,
come già fai in spark_bronze.bash) e restano vivi come processi di lungo
periodo dentro il container spark-master.

Se questo DAG li "lanciasse" a ogni run pianificata, ogni esecuzione
aggiungerebbe un NUOVO consumer Kafka concorrente sullo stesso topic invece
di riavviare quello esistente — dati duplicati o comportamento indefinito.
Per questo il DAG non fa spark-submit dei job di streaming: verifica solo,
via la REST API dello Spark Master, che siano vivi, e orchestra la parte
BATCH a valle (che invece è corretto far girare a intervalli):

  check_streaming_alive → dbt_build_gold → great_expectations_validate

Se lo streaming non risulta attivo, il DAG fallisce subito (fail-fast):
non ha senso far girare dbt su dati che non vengono più aggiornati.
"""

from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowFailException

SPARK_MASTER_UI = "http://spark-master:8080"
REQUIRED_STREAMING_APPS = {"CDC_bronze", "CDC_silver"}

default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def check_streaming_alive():
    """Interroga la REST API dello Spark Master e verifica che bronze e
    silver risultino tra le applicazioni ATTIVE (non 'completed' o assenti).
    Non prova a riavviarli: il riavvio automatico di un job di streaming è
    un'operazione delicata (gestione checkpoint/offset) che va decisa da un
    umano, non innescata da un DAG batch."""
    resp = requests.get(f"{SPARK_MASTER_UI}/json/", timeout=10)
    resp.raise_for_status()
    active = {app["name"] for app in resp.json().get("activeapps", [])}

    missing = REQUIRED_STREAMING_APPS - active
    if missing:
        raise AirflowFailException(
            f"Job di streaming non attivi: {missing}. "
            f"Avviali con spark_apps/spark_bronze.bash / spark_silver.bash "
            f"prima di far girare la pipeline batch a valle."
        )


with DAG(
    dag_id="cdc_batch_pipeline",
    description="Verifica streaming CDC attivo, poi build gold (dbt) e validazione (Great Expectations)",
    default_args=default_args,
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,  # non sovrapporre run se una build gold dura più di un'ora
    tags=["cdc", "batch"],
) as dag:
    check_streaming = PythonOperator(
        task_id="check_streaming_alive",
        python_callable=check_streaming_alive,
    )

    # `docker compose run --rm <servizio>` invece di `docker exec`: il
    # servizio `dbt` ha `profiles: ["tools"]`, quindi non è detto sia già
    # avviato. `run` crea un container usa-e-getta con la stessa immagine/
    # comando/rete definiti nel compose, senza dipendere da uno stato
    # pregresso — più adatto a un task pianificato e idempotente.
    dbt_build_gold = BashOperator(
        task_id="dbt_build_gold",
        bash_command=(
            "docker compose -f docker-compose.yaml -f docker-compose.airflow.yml "
            "run --rm dbt dbt build --profiles-dir /usr/app"
        ),
    )

    # Il servizio great-expectations ha già il comando (spark-submit validate.py)
    # definito nel compose: `run --rm` senza argomenti extra lo riusa così com'è.
    ge_validate = BashOperator(
        task_id="great_expectations_validate",
        bash_command=(
            "docker compose -f docker-compose.yaml -f docker-compose.airflow.yml "
            "run --rm great-expectations"
        ),
    )

    check_streaming >> dbt_build_gold >> ge_validate
