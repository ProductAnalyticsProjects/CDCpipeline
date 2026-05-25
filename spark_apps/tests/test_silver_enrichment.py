import pytest
import tempfile
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
    DoubleType,
    LongType,
    IntegerType,
)
from spark_apps.silver_transforms import enrich_orders
from spark_apps.cdc_silver import make_process_batch


# ── fixture SparkSession senza Delta (unit test) ──────────────────────────────
@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder.master("local[*]").appName("test_silver").getOrCreate()


# ── fixture dati mock ─────────────────────────────────────────────────────────
@pytest.fixture
def upserts_df(spark):
    schema = StructType(
        [
            StructField("id", StringType(), True),
            StructField("customer_email", StringType(), True),
            StructField("status", StringType(), True),
            StructField("total_amount", DoubleType(), True),
            StructField("cdc_op", StringType(), True),
        ]
    )
    data = [
        ("uuid-order-1", "mario@gmail.com", "PENDING", 100.0, "c"),
        ("uuid-order-2", "senza@utente.com", "PENDING", 50.0, "u"),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def user_df(spark):
    schema = StructType(
        [
            StructField("id", StringType(), True),
            StructField("email", StringType(), True),
            StructField("role", StringType(), True),
            StructField("created_at", LongType(), True),
        ]
    )
    return spark.createDataFrame(
        [("uuid-user-1", "mario@gmail.com", "CUSTOMER", 1700000000)], schema
    )


@pytest.fixture
def item_df(spark):
    schema = StructType(
        [
            StructField("order_id", StringType(), True),
            StructField("items_count", IntegerType(), True),
        ]
    )
    return spark.createDataFrame([("uuid-order-1", 3)], schema)


# ── unit test: enrich_orders ──────────────────────────────────────────────────
def test_enrichment_aggiunge_email_utente(upserts_df, user_df, item_df):
    risultato = enrich_orders(upserts_df, user_df, item_df)
    riga = risultato.filter(col("id") == "uuid-order-1").first()
    assert riga["user_email"] == "mario@gmail.com"


def test_utente_non_trovato_genera_null(upserts_df, user_df, item_df):
    risultato = enrich_orders(upserts_df, user_df, item_df)
    riga = risultato.filter(col("id") == "uuid-order-2").first()
    assert riga["user_email"] is None


def test_enrichment_aggiunge_conteggio_items(upserts_df, user_df, item_df):
    risultato = enrich_orders(upserts_df, user_df, item_df)
    riga = risultato.filter(col("id") == "uuid-order-1").first()
    assert riga["items_count"] == 3


def test_ordine_senza_items_ha_items_count_null(upserts_df, user_df, item_df):
    risultato = enrich_orders(upserts_df, user_df, item_df)
    riga = risultato.filter(col("id") == "uuid-order-2").first()
    assert riga["items_count"] is None


# ── integration test: process_batch con Delta ─────────────────────────────────
# Richiedono i JAR Delta — disponibili nell'immagine Docker, non in locale
@pytest.mark.integration
def test_process_batch_insert(spark, upserts_df, user_df, item_df):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark, user_df, item_df, tmp)
        process_batch(upserts_df, batch_id=0)
        result = spark.read.format("delta").load(f"{tmp}/silver/orders")
        assert result.count() == 2
        assert (
            result.filter(col("id") == "uuid-order-1").first()["user_email"]
            == "mario@gmail.com"
        )


@pytest.mark.integration
def test_process_batch_delete(spark, upserts_df, user_df, item_df):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark, user_df, item_df, tmp)
        process_batch(upserts_df, batch_id=0)

        delete_schema = StructType(
            [
                StructField("id", StringType(), True),
                StructField("customer_email", StringType(), True),
                StructField("status", StringType(), True),
                StructField("total_amount", DoubleType(), True),
                StructField("cdc_op", StringType(), True),
            ]
        )
        deletes_df = spark.createDataFrame(
            [("uuid-order-1", "mario@gmail.com", "PENDING", 100.0, "d")], delete_schema
        )
        process_batch(deletes_df, batch_id=1)

        result = spark.read.format("delta").load(f"{tmp}/silver/orders")
        assert result.count() == 1
        assert result.filter(col("id") == "uuid-order-1").count() == 0
