import os

import pytest

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")


@pytest.fixture(scope="session")
def spark_delta():
    """SparkSession con il JAR Delta vero, per i test che fanno write/MERGE
    su Delta (marcati @pytest.mark.integration).

    In Docker il JAR arriva pre-installato (dockerfile); in locale e in CI
    configure_spark_with_delta_pip lo scarica da Maven al primo avvio (serve
    internet la prima volta). extensions/catalog vanno messi PRIMA di
    configure_spark_with_delta_pip, che da solo aggiunge solo il jar: senza,
    .write.format("delta") funziona ma la MERGE no.

    Attenzione: SparkSession è un singleton per processo. Se nello stesso
    run un altro test ha già creato una sessione SENZA Delta, getOrCreate()
    restituisce quella e la MERGE fallisce. Per questo in CI i test
    `integration` girano in uno step separato da quelli unitari, e i test
    che usano questa fixture la chiedono come PRIMO argomento.
    """
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.master("local[*]")
        .appName("test_silver_delta")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()
