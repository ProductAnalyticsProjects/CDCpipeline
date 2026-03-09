from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, lit
from pyspark.sql.types import (
    StructField,
    StructType,
    IntegerType,
    DoubleType,
    StringType,
)

spark = SparkSession.builder.appName("CDC_bronze").getOrCreate()

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
    .option("subscribe", "inventory.public.orders")
    .load()
)

bronze_df = (
    raw_df.selectExpr("CAST(value AS STRING)")
    .select(from_json(col("value"), order_schema).alias("data"))
    .select("data.*")
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn(
        "source_file",
        col("_medata.file_path") if "_metadata" in raw_df.columns else lit(None),
    )
)

query = (
    bronze_df.writeStream.format("delta")
    .option("checkpointLocation", "/mnt/spark_checkpoints/bronze_users")
    .outputMode("append")
    .start("/opt/spark/work-dir/bronze/users")
)

query.awaitTermination()
