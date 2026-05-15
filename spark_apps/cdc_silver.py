from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import os
import logging
from delta.tables import DeltaTable


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
BUCKET = "lakehouse"
CHECKPOINT_BUCKET = "spark-checkpoints"

logger.info("Inizializzazione Spark session")

spark = (
    SparkSession.builder.appName("CDC_silver")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    # --- S3A / MinIO ---
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS)
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")  # obbligatorio per MinIO
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config(
        "spark.hadoop.fs.s3a.aws.credentials.provider",
        "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
    )
    .config(
        "spark.delta.logStore.s3a.impl", "io.delta.storage.S3SingleDriverLogStore"
    )  # Delta su S3-compatible
    .getOrCreate()
)

POSTGRES_URL = "jdbc:postgresql://postgres:5432/fullfillment"
POSTGRES_PROPERTIES = {
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
    "driver": "org.postgresql.Driver",
}

logger.info("Lettura dati utenti da Postgres")
user_df = (
    spark.read.format("jdbc")
    .option("url", POSTGRES_URL)
    .option("dbtable", "public.users")
    .options(**POSTGRES_PROPERTIES)
    .load()
    .select("id", "email", "name", "registered_at", "country")
    .cache()
)

logger.info("Lettura order items da Postgres")
item_df = (
    spark.read.format("jdbc")
    .option("url", POSTGRES_URL)
    .option("dbtable", "public.order_items")
    .options(**POSTGRES_PROPERTIES)
    .load()
    .groupBy("order_id")
    .count()
    .withColumnRenamed("count", "items_count")
    .cache()
)


def process_batch(batch_df, batch_id):
    silver_path = f"s3a://{BUCKET}/silver/orders"

    upserts = batch_df.filter(col("cdc_op").isin("c", "u"))
    deletes = batch_df.filter(col("cdc_op") == "d")

    enriched = (
        upserts.join(user_df, upserts.tenant_id == user_df.id, "left")
        .drop(user_df.id)
        .withColumnRenamed("email", "user_email")
        .withColumnRenamed("name", "user_name")
        .join(item_df, upserts.id == item_df.order_id, "left")
        .drop("order_id")
        .drop("cdc_op")
    )

    if not DeltaTable.isDeltaTable(spark, silver_path):
        (enriched.write.format("delta").save(silver_path))
        return

    silver = DeltaTable.forPath(spark, silver_path)

    (
        silver.alias("s")
        .merge(enriched.alias("b"), "s.id = b.id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )

    if deletes.count() > 0:
        (
            silver.alias("s")
            .merge(deletes.alias("b"), "s.id = b.id")
            .whenMatchedDelete()
            .execute()
        )


bronze_stream = spark.readStream.format("delta").load(f"s3a://{BUCKET}/bronze/orders")

try:
    logger.info("Avvio stream CDC silver")
    query = (
        bronze_stream.writeStream.foreachBatch(process_batch)
        .option("checkpointLocation", f"s3a://{CHECKPOINT_BUCKET}/silver/orders")
        .start()
    )
    query.awaitTermination()
    logger.info("Streaming silver terminato")
except Exception as e:
    logger.error("Errore nello stream verso Silver: %s", str(e))
