from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, date_format
from pyspark.sql.types import (
    StructField,
    StructType,
    IntegerType,
    DoubleType,
    StringType,
)
import os

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
BUCKET = "lakehouse"
CHECKPOINT_BUCKET = "spark-checkpoints"

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
        StructField("id", IntegerType(), True),
        StructField("order_number", StringType(), True),
        StructField("amount", DoubleType(), True),
        StructField("tenant_id", IntegerType(), True),
    ]
)

raw_df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "fullfillment.public.orders")
    .load()
)

debezium_schema = StructType(
    [
        StructField(
            "payload",
            StructType(
                [
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

bronze_df = (
    raw_df.selectExpr("CAST(value AS STRING)")
    .select(from_json(col("value"), debezium_schema).alias("debezium"))
    .select(col("debezium.payload.after.*"), col("debezium.payload.op").alias("cdc_op"))
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn("ingestion_date", date_format(col("ingestion_timestamp"), "yyyy-MM-dd"))
)

query = (
    bronze_df.writeStream.format("delta")
    .option("checkpointLocation", f"s3a://{CHECKPOINT_BUCKET}/bronze/orders")
    .outputMode("append")
    .partitionBy("ingestion_date")
    .start(f"s3a://{BUCKET}/bronze/orders")
)

query.awaitTermination()
