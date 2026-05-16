import pytest
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


@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder.master("local[*]").appName("test_silver").getOrCreate()


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
    data = [
        ("uuid-user-1", "mario@gmail.com", "CUSTOMER", 1700000000),
    ]
    return spark.createDataFrame(data, schema)


@pytest.fixture
def item_df(spark):
    schema = StructType(
        [
            StructField("order_id", StringType(), True),
            StructField("items_count", IntegerType(), True),
        ]
    )
    data = [
        ("uuid-order-1", 3),
    ]
    return spark.createDataFrame(data, schema)


def test_enrichment_aggiungi_email_utente(upserts_df, user_df, item_df):
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
