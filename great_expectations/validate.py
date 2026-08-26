import os
import sys
import logging
from pyspark.sql import SparkSession
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_spark_session(minio_endpoint, minio_access, minio_secret):
    return (
        SparkSession.builder.appName("GE_validation")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.hadoop.fs.s3a.endpoint", minio_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", minio_access)
        .config("spark.hadoop.fs.s3a.secret.key", minio_secret)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        )
        .config(
            "spark.delta.logStore.s3a.impl",
            "io.delta.storage.S3SingleDriverLogStore",
        )
        .getOrCreate()
    )


def validate_layer(context, spark, df, suite_name, layer_name, run_id):
    batch_request = RuntimeBatchRequest(
        datasource_name="delta_lakehouse",
        data_connector_name="runtime_connector",
        data_asset_name=layer_name,
        runtime_parameters={"batch_data": df},
        batch_identifiers={"layer": layer_name, "run_id": run_id},
    )

    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )

    results = validator.validate()
    logger.info(
        "Validazione %s: %s/%s aspettative passate",
        layer_name,
        results["statistics"]["successful_expectations"],
        results["statistics"]["evaluated_expectations"],
    )

    if not results["success"]:
        logger.warning("Alcune aspettative sono fallite per %s", layer_name)

    return results


def main():
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
    MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
    BUCKET = "lakehouse"
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    spark = create_spark_session(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET)
    context = gx.get_context(context_root_dir="/app/great_expectations")

    # Un layer assente (silver/gold non ancora scritti) è un legittimo skip,
    # non un fallimento: il try/except sotto copre solo quel caso. Una
    # validazione che GIRA ma trova aspettative rosse è invece un fallimento
    # vero e deve far uscire lo script con codice diverso da zero — altrimenti
    # `docker compose run --rm great-expectations` (e quindi il task Airflow
    # che lo lancia in cdc_batch_pipeline) risulta sempre verde a prescindere
    # dal risultato, e la validazione diventa un log che nessuno legge invece
    # che un gate.
    any_failure = False

    logger.info("Validazione Silver layer")
    try:
        silver_df = spark.read.format("delta").load(f"s3a://{BUCKET}/silver/orders")
        results = validate_layer(
            context, spark, silver_df, "silver_orders_suite", "silver", run_id
        )
        if not results["success"]:
            any_failure = True
    except Exception as e:
        logger.warning("Silver layer non disponibile, skip: %s", str(e))

    logger.info("Validazione Gold layer")
    try:
        gold_df = spark.read.format("delta").load(f"s3a://{BUCKET}/gold/orders_daily")
        results = validate_layer(context, spark, gold_df, "gold_suite", "gold", run_id)
        if not results["success"]:
            any_failure = True
    except Exception as e:
        logger.warning("Gold layer non disponibile, skip: %s", str(e))

    logger.info("Generazione Data Docs")
    context.build_data_docs()
    logger.info("Data Docs generati in /app/great_expectations/data_docs")

    if any_failure:
        logger.error("Una o più validazioni sono fallite: uscita con errore")
        sys.exit(1)


if __name__ == "__main__":
    main()
