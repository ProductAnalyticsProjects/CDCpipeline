import logging
import os

from pyspark.sql import SparkSession

from spark_apps.bronze_transforms import (
    ORDER_ITEM_ROW_SCHEMA,
    ORDER_ROW_SCHEMA,
    USER_ROW_SCHEMA,
    build_bronze_df,
    build_bronze_outbox_df,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Una tabella = un topic Kafka = uno stream = un path Bronze: lo stesso script
# gira una volta per tabella (selezionata via BRONZE_TABLE), invece di 4 file
# quasi identici. L'orchestrazione di quale job lanciare quale tabella
# (Airflow) resta fuori da questo spike.
TABLE_CONFIGS = {
    "orders": {
        "topic": "fullfillment.public.orders",
        "row_schema": ORDER_ROW_SCHEMA,
        "decimal_columns": {"total_amount": 4},
    },
    "users": {
        "topic": "fullfillment.public.users",
        "row_schema": USER_ROW_SCHEMA,
        "decimal_columns": {},
    },
    "order_items": {
        "topic": "fullfillment.public.order_items",
        "row_schema": ORDER_ITEM_ROW_SCHEMA,
        "decimal_columns": {"unit_price": 4, "subtotal": 4},
    },
    # outbox_events non è nella mappa: dopo l'EventRouter SMT il topic ha una
    # forma diversa dall'envelope Debezium standard (vedi
    # build_bronze_outbox_df) e va letto con un topic pattern, non un nome
    # fisso — gestito a parte in main().
}
OUTBOX_TOPIC_PATTERN = r"outbox\.event\..*"


def create_spark_session(minio_endpoint, minio_access, minio_secret):
    return (
        SparkSession.builder.appName("CDC_bronze")
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


def main():
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
    MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
    BUCKET = "lakehouse"
    CHECKPOINT_BUCKET = "spark-checkpoints"
    BRONZE_TABLE = os.environ.get("BRONZE_TABLE", "orders")

    logger.info("Inizializzazione Spark session")
    spark = create_spark_session(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET)

    if BRONZE_TABLE == "outbox_events":
        logger.info("Connessione a Kafka: topic pattern %s", OUTBOX_TOPIC_PATTERN)
        raw_df = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", "kafka:29092")
            .option("subscribePattern", OUTBOX_TOPIC_PATTERN)
            .option("startingOffsets", "earliest")
            .load()
        )
        bronze_df = build_bronze_outbox_df(raw_df)
        bronze_path = f"s3a://{BUCKET}/bronze/outbox_events"
        checkpoint_path = f"s3a://{CHECKPOINT_BUCKET}/bronze/outbox_events"
    else:
        config = TABLE_CONFIGS[BRONZE_TABLE]
        logger.info("Connessione a Kafka: topic %s", config["topic"])
        raw_df = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", "kafka:29092")
            .option("subscribe", config["topic"])
            .option(
                "startingOffsets", "earliest"
            )  # al primo avvio legge tutto il topic; i riavvii successivi usano il checkpoint
            .load()
        )
        bronze_df = build_bronze_df(
            raw_df, config["row_schema"], config["decimal_columns"]
        )
        bronze_path = f"s3a://{BUCKET}/bronze/{BRONZE_TABLE}"
        checkpoint_path = f"s3a://{CHECKPOINT_BUCKET}/bronze/{BRONZE_TABLE}"

    try:
        logger.info("Avvio stream CDC bronze per %s", BRONZE_TABLE)
        query = (
            bronze_df.writeStream.format("delta")
            .option("checkpointLocation", checkpoint_path)
            .outputMode("append")
            .partitionBy("ingestion_date")
            .start(bronze_path)
        )
        query.awaitTermination()
        logger.info("Stream terminato")
    except Exception as e:
        logger.error("Errore stream %s", str(e))


if __name__ == "__main__":
    main()
