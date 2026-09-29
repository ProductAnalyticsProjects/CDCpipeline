# spark_apps/maintenance/vacuum.py
import logging
import os
import sys

from delta.tables import DeltaTable
from pyspark.sql import SparkSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]

spark = (
    SparkSession.builder.appName("delta_vacuum")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS)
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config(
        "spark.hadoop.fs.s3a.aws.credentials.provider",
        "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
    )
    .config("spark.delta.logStore.s3a.impl", "io.delta.storage.S3SingleDriverLogStore")
    # Nessun override di retentionDurationCheck: la retention usata qui (168h)
    # è già il default di Delta, disabilitare il check serviva solo a
    # permettere retention più basse, che non usiamo.
    .getOrCreate()
)

# Retention esplicita invece del default implicito: è anche l'orizzonte
# massimo di time travel, quindi va tenuta allineata al replay più lungo che
# ci si aspetta di dover fare (Fase 5).
RETENTION_HOURS = 168

# Solo le tabelle scritte da Spark. Gold non è qui: la scrive dbt via Trino
# (materialized: table), che ricrea la tabella a ogni run invece di
# accumulare versioni — e il vecchio path gold/orders non è mai esistito.
# Su Bronze (append-only) VACUUM trova poco o niente da rimuovere: i file
# diventano obsoleti solo dopo MERGE, OPTIMIZE o overwrite. Resta in lista
# perché è innocuo e diventa utile appena si introduce OPTIMIZE.
TABLES = [
    "s3a://lakehouse/bronze/orders",
    "s3a://lakehouse/bronze/users",
    "s3a://lakehouse/bronze/order_items",
    "s3a://lakehouse/bronze/outbox_events",
    "s3a://lakehouse/silver/orders",
]

logger.info("Avvio job spark")
failed = []
for path in TABLES:
    if not DeltaTable.isDeltaTable(spark, path):
        # Uno stream mai avviato per quella tabella non è un errore di
        # manutenzione: si salta, senza far fallire il DAG.
        logger.warning("Tabella Delta assente, salto: %s", path)
        continue
    logger.info("VACUUM → %s", path)
    try:
        DeltaTable.forPath(spark, path).vacuum(retentionHours=RETENTION_HOURS)
        logger.info("VACUUM completato %s", path)
    except Exception:
        logger.exception("Errore VACUUM su %s", path)
        failed.append(path)

spark.stop()

# Exit code != 0 se almeno una tabella esistente fallisce: prima l'errore
# veniva solo loggato e il task Airflow risultava comunque verde.
if failed:
    logger.error("VACUUM fallito su: %s", failed)
    sys.exit(1)
