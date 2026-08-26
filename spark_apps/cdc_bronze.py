from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, date_format, when, udf
from pyspark.sql.types import (
    StructField,
    StructType,
    LongType,
    StringType,
    TimestampType,
    DecimalType
)
import os
import logging
from spark_apps.bronze_transforms import convert_base_to_decimal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
BUCKET = "lakehouse"
CHECKPOINT_BUCKET = "spark-checkpoints"

logger.info("Inizializzazione Spark session")
spark = (
    SparkSession.builder.appName("CDC_bronze")
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

order_schema = StructType(
    [
        StructField("id", StringType(), True),
        StructField("customer_email", StringType(), True),
        StructField("status", StringType(), True),
        StructField("total_amount", StringType(), True),
        StructField("notes", StringType(), True),
        StructField("created_at", TimestampType(), True),
        StructField("updated_at", TimestampType(), True),
        StructField("version", LongType(), True),
        StructField("idempotency_key", StringType(), True),
    ]
)

logger.info("Connessione a Kafka")
raw_df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "fullfillment.public.orders")
    .option(
        "startingOffsets", "earliest"
    )  # al primo avvio legge tutto il topic; i riavvii successivi usano il checkpoint
    .load()
)

debezium_schema = StructType(
    [
        StructField(
            "payload",
            StructType(
                [
                    StructField("before", order_schema, True),
                    StructField("after", order_schema, True),
                    StructField(
                        "op", StringType(), True
                    ),  # "c"=insert, "u"=update, "d"=delete
                ]
            ),
            True,
        )
    ]
)

converter_udf = udf(convert_base_to_decimal, returnType=DecimalType(19,4))

bronze_df = (
    raw_df.selectExpr("CAST(value AS STRING)")
    .select(from_json(col("value"), debezium_schema).alias("debezium"))
    .select(
        when(col("debezium.payload.op") == "d", col("debezium.payload.before"))
        .otherwise(col("debezium.payload.after"))
        .alias("data"),
        col("debezium.payload.op").alias("cdc_op"),
    )
    .select("data.*", "cdc_op")
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn("ingestion_date", date_format(col("ingestion_timestamp"), "yyyy-MM-dd"))
    .withColumn('total_amount_decoded', converter_udf(col("total_amount")))
    .na.drop(subset="cdc_op")
)

try:
    logger.info("Avvio stream CDC bronze")
    query = (
        bronze_df.writeStream.format("delta")
        .option("checkpointLocation", f"s3a://{CHECKPOINT_BUCKET}/bronze/orders")
        .outputMode("append")
        .partitionBy("ingestion_date")
        .start(f"s3a://{BUCKET}/bronze/orders")
    )
    query.awaitTermination()
    logger.info("Stream terminato")
except Exception as e:
    logger.error("Errore stream %s", str(e))
