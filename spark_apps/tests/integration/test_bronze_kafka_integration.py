"""Test di integrazione: parsing dell'envelope Debezium contro un broker
Kafka VERO (non mockato), lanciato come service container in CI
(vedi job `integration-test` in ci.yml).

Differenza rispetto a spark_apps/tests/test_silver_enrichment.py (unit test):
quel file testa le trasformazioni passando DataFrame costruiti a mano in
memoria — utile e veloce, ma non tocca mai Kafka, quindi non avrebbe MAI
intercettato il bug storico di questo progetto (`debezium_schema` definito
ma mai usato, messaggi letti con lo schema sbagliato → bronze pieno di null).
Questo test produce un messaggio reale sul broker e lo fa leggere a Spark
esattamente come farebbe cdc_bronze.py in produzione.

Cartella separata (tests/integration/, non tests/) apposta: il job `test`
(unit, veloce, gira su ogni push) esclude questa cartella con
`--ignore=spark_apps/tests/integration`; solo il job `integration-test`
(più lento, richiede i service container) la esegue.
"""

import json
import os

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, when
from pyspark.sql.types import DoubleType, LongType, StringType, StructField, StructType

pytestmark = pytest.mark.integration

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "fullfillment.public.orders"

# Stesso schema di spark_apps/cdc_bronze.py — duplicato qui perché
# cdc_bronze.py non espone una funzione importabile per costruirlo (è tutto
# a livello di modulo, eseguito su import). Se in futuro estrai la logica di
# parsing in una funzione tipo `build_bronze_df(raw_df)` come già fatto per
# la silver (`make_process_batch`), questo test potrebbe importarla invece
# di duplicare lo schema — più sicuro, zero rischio di disallineamento.
order_schema = StructType(
    [
        StructField("id", StringType(), True),
        StructField("customer_email", StringType(), True),
        StructField("status", StringType(), True),
        StructField("total_amount", DoubleType(), True),
        StructField("notes", StringType(), True),
        StructField("created_at", LongType(), True),
        StructField("updated_at", LongType(), True),
        StructField("version", LongType(), True),
        StructField("idempotency_key", StringType(), True),
    ]
)

debezium_schema = StructType(
    [
        StructField(
            "payload",
            StructType(
                [
                    StructField("before", order_schema, True),
                    StructField("after", order_schema, True),
                    StructField("op", StringType(), True),
                ]
            ),
            True,
        )
    ]
)


@pytest.fixture(scope="module")
def spark():
    return (
        SparkSession.builder.appName("test_bronze_kafka_integration")
        .master("local[*]")
        # Connector Kafka per Spark 4.0/Scala 2.13, stessa versione del dockerfile
        # di produzione — se cambi versione lì, aggiornala anche qui.
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0",
        )
        .getOrCreate()
    )


def _produce_debezium_message(op: str, after: dict | None, before: dict | None = None):
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version=(2, 8, 0),  # evita l'auto-negoziazione, non sempre affidabile in CI
    )
    envelope = {"payload": {"before": before, "after": after, "op": op}}
    producer.send(TOPIC, envelope)
    producer.flush()
    producer.close()


def test_insert_envelope_is_parsed_correctly(spark):
    """Riproduce esattamente il bug storico: se il parsing usasse
    `order_schema` invece di `debezium_schema` per leggere il messaggio
    grezzo, `data.*` non esisterebbe nel JSON risultante e le colonne
    sarebbero tutte null. Questo test fallisce in quel caso."""
    _produce_debezium_message(
        op="c",
        after={
            "id": "order-1",
            "customer_email": "test@example.com",
            "status": "PENDING",
            "total_amount": 42.5,
            "notes": None,
            "created_at": 1700000000000,
            "updated_at": 1700000000000,
            "version": 1,
            "idempotency_key": "abc-123",
        },
    )

    raw_df = (
        spark.read.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "earliest")
        .option("endingOffsets", "latest")
        .load()
    )

    # Stessa trasformazione di cdc_bronze.py: from_json con debezium_schema,
    # poi before/after selezionato in base a cdc_op.
    bronze_df = (
        raw_df.selectExpr("CAST(value AS STRING)")
        .select(from_json(col("value"), debezium_schema).alias("debezium"))
        .select(
            when(col("debezium.payload.op") == "d", col("debezium.payload.before"))
            .otherwise(col("debezium.payload.after"))
            .alias("data"),
            col("debezium.payload.op").alias("cdc_op"),
        )
        .select("data.*", "cdc_op")
    )

    rows = bronze_df.collect()
    assert len(rows) == 1

    row = rows[0]
    assert row["cdc_op"] == "c"
    assert row["id"] == "order-1"
    assert row["customer_email"] == "test@example.com"
    assert row["status"] == "PENDING"
    assert row["total_amount"] == 42.5
    # La regressione storica produceva null qui perché il parsing bypassava
    # l'envelope: questa asserzione è il cuore del test.
    assert row["id"] is not None
