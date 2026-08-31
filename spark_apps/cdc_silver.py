from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import os
import logging
from delta.tables import DeltaTable
from spark_apps.silver_transforms import enrich_orders


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_spark_session(minio_endpoint, minio_access, minio_secret):
    spark = (
        SparkSession.builder.appName("CDC_silver")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        # --- S3A / MinIO ---
        .config("spark.hadoop.fs.s3a.endpoint", minio_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", minio_access)
        .config("spark.hadoop.fs.s3a.secret.key", minio_secret)
        .config(
            "spark.hadoop.fs.s3a.path.style.access", "true"
        )  # obbligatorio per MinIO
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
    return spark


def make_process_batch(spark, user_df, item_df, silver_base_path):
    def process_batch(batch_df, batch_id):
        logger.info("Elaborazione batch %s", batch_id)
        silver_path = f"{silver_base_path}/silver/orders"

        upserts = batch_df.filter(col("cdc_op").isin("c", "u"))
        deletes = batch_df.filter(col("cdc_op") == "d")

        enriched = enrich_orders(upserts, user_df, item_df)

        if not DeltaTable.isDeltaTable(spark, silver_path):
            enriched.write.format("delta").save(silver_path)
            return

        silver = DeltaTable.forPath(spark, silver_path)

        cond = """
            (s.updated_at < b.updated_at AND b.updated_at IS NOT NULL)
                OR (s.version < b.version AND (b.updated_at IS NULL OR s.updated_at = b.updated_at))
                OR (s.updated_at IS NULL AND b.updated_at IS NOT NULL)
        """
        (
            silver.alias("s")
            .merge(enriched.alias("b"), "s.id = b.id")
            .whenMatchedUpdateAll(cond)
            .whenNotMatchedInsertAll()
            .execute()
        )

        if deletes.count() > 0:
            (
                silver.alias("s")
                .merge(deletes.alias("b"), "s.id = b.id")
                .whenMatchedDelete(cond)
                .execute()
            )

    return process_batch


def main():
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
    MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
    BUCKET = "lakehouse"
    CHECKPOINT_BUCKET = "spark-checkpoints"

    POSTGRES_URL = "jdbc:postgresql://postgres:5432/inventory"
    POSTGRES_PROPERTIES = {
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "driver": "org.postgresql.Driver",
    }
    SILVER_BASE_PATH = f"s3a://{BUCKET}"

    logger.info("Inizializzazione Spark session")
    spark = create_spark_session(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET)

    logger.info("Lettura dati utenti da Postgres")
    user_df = (
        spark.read.format("jdbc")
        .option("url", POSTGRES_URL)
        .option("dbtable", "public.users")
        .options(**POSTGRES_PROPERTIES)
        .load()
        .select("id", "email", "role", "created_at")
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
    )

    process_batch = make_process_batch(spark, user_df, item_df, SILVER_BASE_PATH)
    bronze_stream = spark.readStream.format("delta").load(
        f"s3a://{BUCKET}/bronze/orders"
    )

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


if __name__ == "__main__":
    main()
