from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructField, StructType, IntegerType, DoubleType, StringType

spark = SparkSession.builder.appName('CDC-final') \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate() 

order_schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("order_number", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("tenant_id", IntegerType(), True)
    ])

raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "inventory.puclic.orders") \
    .load()

query = raw_df.selectExpr("CAST(value AS STRING) as json_str") \
    .writeStream \
    .option("checkpointLocation", "/mnt/spark_checkpoints/cdc_query_1") \
    .outputMode("append").format("console").start()

query.awaitTermination()