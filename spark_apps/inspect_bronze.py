import os

from pyspark.sql import SparkSession

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
BRONZE_TABLE = os.environ.get("BRONZE_TABLE", "orders")

spark = (
    SparkSession.builder.appName("inspect_bronze")
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
    .getOrCreate()
)

bronze_df = spark.read.format("delta").load(f"s3a://lakehouse/bronze/{BRONZE_TABLE}")

bronze_df.printSchema()
bronze_df.show(truncate=False)

bronze_df.createOrReplaceTempView("bronze_table")

# outbox_events (post-EventRouter) non ha cdc_op, ha event_type — vedi
# build_bronze_outbox_df in spark_apps/bronze_transforms.py.
group_column = "event_type" if BRONZE_TABLE == "outbox_events" else "cdc_op"
result = spark.sql(f"""
    SELECT ingestion_date, {group_column}, COUNT(*) as record_count
    FROM bronze_table
    GROUP BY ingestion_date, {group_column}
    ORDER BY ingestion_date DESC
""")
result.show()
