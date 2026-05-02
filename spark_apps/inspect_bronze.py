from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("inspect_bronze")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )
    .getOrCreate()
)

bronze_df = spark.read.format("delta").load("/opt/spark/data_lake/bronze/users")

# Mostriamo lo schema e i primi dati
bronze_df.printSchema()
bronze_df.show(truncate=False)

bronze_df.createOrReplaceTempView("bronze_user")
spark.sql("Select ingestion_date, count(*) from bronze_user group by ingestion_date")
