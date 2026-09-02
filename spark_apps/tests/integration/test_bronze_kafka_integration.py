"""Test di integrazione: parsing dell'envelope Debezium contro un broker
Kafka VERO (non mockato), lanciato come service container in CI
(vedi job `integration-test` in ci.yml).

Differenza rispetto a spark_apps/tests/test_silver_enrichment.py (unit test):
quel file testa le trasformazioni passando DataFrame costruiti a mano in
memoria — utile e veloce, ma non tocca mai Kafka, quindi non avrebbe MAI
intercettato il bug storico di questo progetto (`debezium_schema` definito
ma mai usato, messaggi letti con lo schema sbagliato → bronze pieno di null).
Questo test produce un messaggio reale sul broker e lo fa leggere a Spark
esattamente come farebbe cdc_bronze.py in produzione — stessa funzione
(`build_bronze_df`, importata da `spark_apps.bronze_transforms` invece di
duplicare lo schema: prima della Fase 1 questo file teneva una copia propria
di `order_schema`/`debezium_schema`, che poteva disallinearsi in silenzio da
quella reale — vedi ROADMAP.md, Fase 1).

`total_amount` è codificato in base64 (stesso formato reale osservato su
Kafka, non un `DoubleType` semplificato) e `created_at`/`updated_at` sono
stringhe ISO-8601 con offset, come le produce davvero Debezium con
`time.precision.mode: adaptive_time_microseconds` su una colonna TIMESTAMPTZ
— prima di questo file i dati sintetici non erano realistici (vedi
ROADMAP.md, nota a margine Fase 0.3): la conversione base64→decimal e il
parsing timestamp non venivano quindi mai esercitati da questo test.

Cartella separata (tests/integration/, non tests/) apposta: il job `test`
(unit, veloce, gira su ogni push) esclude questa cartella con
`--ignore=spark_apps/tests/integration`; solo il job `integration-test`
(più lento, richiede i service container) la esegue.
"""

import base64
import json
import os
from decimal import Decimal

import pytest
from pyspark.sql import SparkSession

from spark_apps.bronze_transforms import ORDER_ROW_SCHEMA, build_bronze_df

pytestmark = pytest.mark.integration

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "fullfillment.public.orders"


def _encode_decimal(value: str, scale: int = 4) -> str:
    """Stesso formato di Debezium con decimal.handling.mode=precise: bytes
    big-endian, complemento a due, poi base64. Vedi
    spark_apps/tests/test_bronze_transforms.py per il valore noto 'Bnwo'."""
    unscaled = int(Decimal(value).scaleb(scale))
    length = max(1, (unscaled.bit_length() + 8) // 8)
    return base64.b64encode(
        unscaled.to_bytes(length, byteorder="big", signed=True)
    ).decode()


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
    """Riproduce esattamente il bug storico: se il parsing usasse lo schema
    della riga invece dell'envelope Debezium completo per leggere il
    messaggio grezzo, `data.*` non esisterebbe nel JSON risultante e le
    colonne sarebbero tutte null. Questo test fallisce in quel caso — e con
    dati realistici (base64/ISO-8601) esercita anche la stessa decodifica
    che gira in produzione."""
    _produce_debezium_message(
        op="c",
        after={
            "id": "order-1",
            "customer_email": "test@example.com",
            "status": "PENDING",
            "total_amount": _encode_decimal("42.50"),
            "notes": None,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
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

    bronze_df = build_bronze_df(
        raw_df, ORDER_ROW_SCHEMA, decimal_columns={"total_amount": 4}
    )

    rows = bronze_df.collect()
    assert len(rows) == 1

    row = rows[0]
    assert row["cdc_op"] == "c"
    assert row["id"] == "order-1"
    assert row["customer_email"] == "test@example.com"
    assert row["status"] == "PENDING"
    # La regressione storica produceva null qui perché il parsing bypassava
    # l'envelope: questa asserzione è il cuore del test.
    assert row["id"] is not None
    assert row["total_amount_decoded"] == Decimal("42.5000")
    assert row["created_at"] is not None
    assert row["source_lsn"] is None  # non impostato in questo messaggio sintetico
