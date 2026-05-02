from pyspark.sql import SparkSession

MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS = "minioadmin"
MINIO_SECRET = "minioadmin"

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

bronze_df = spark.read.format("delta").load("s3a://lakehouse/bronze/orders")

bronze_df.printSchema()
bronze_df.show(truncate=False)

bronze_df.createOrReplaceTempView("bronze_orders")

result = spark.sql("""
    SELECT ingestion_date, cdc_op, COUNT(*) as record_count
    FROM bronze_orders
    GROUP BY ingestion_date, cdc_op
    ORDER BY ingestion_date DESC
""")
result.show()
