# Immagine Airflow + Docker CLI.
#
# Perché serve il Docker CLI dentro il container Airflow: i DAG orchestrano
# dbt e Great Expectations lanciandoli con `docker compose run --rm <servizio>`,
# lo stesso comando che useresti a mano da terminale — Airflow diventa lo
# "scheduler" di comandi che già conosci, non un sistema parallelo da imparare
# da zero. Per farlo, il container Airflow deve poter parlare col demone
# Docker dell'host: monta il socket (vedi docker-compose.airflow.yml) e qui
# installiamo il client `docker`.
#
# Nota di sicurezza: montare /var/run/docker.sock dentro un container dà a
# quel container controllo equivalente a root sull'host (può creare/ispezionare
# qualsiasi container). Accettabile per uno stack locale/portfolio come questo;
# in produzione si usa un executor remoto (KubernetesExecutor, CeleryExecutor
# con worker dedicati) o un operator che parla con l'API Docker via TCP+TLS,
# non il socket montato direttamente.
FROM apache/airflow:3.3.1-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt
