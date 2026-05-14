# spark_apps/maintenance/vacuum.py
from delta.tables import DeltaTable
from pyspark.sql import SparkSession
import os
import logging

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
    # Necessario per abbassare la retention sotto i 7 giorni default
    .config("spark.databricks.delta.retentionDurationCheck.enabled", "false")
    .getOrCreate()
)

TABLES = [
    "s3a://lakehouse/bronze/orders",
    "s3a://lakehouse/silver/orders",
    "s3a://lakehouse/gold/orders",
]

logger.info("Avvio job spark")
for path in TABLES:
    logger.info("VACUUM → %s", path)
    try:
        dt = DeltaTable.forPath(spark, path)
        dt.vacuum(retentionHours=168)
        logger.info("VACUUM completato %s", path)
    except Exception as e:
        logger.error("Errore Vacuum: %s", str(e))

spark.stop()
