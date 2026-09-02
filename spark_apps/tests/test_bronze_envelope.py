# Fase 1 — Bronze come vero event store (ROADMAP.md). Criterio di uscita:
# "da Bronze si può ricostruire lo stato di orders a un timestamp arbitrario
# usando solo i suoi campi" — questi test coprono i cinque casi richiesti
# (op=r snapshot, c, u, d, tombstone) su `build_bronze_df`, con DataFrame
# costruiti a mano: nessun Kafka reale (quello è in
# tests/integration/test_bronze_kafka_integration.py).
import json
from decimal import Decimal

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from spark_apps.bronze_transforms import (
    ORDER_ROW_SCHEMA,
    build_bronze_df,
    build_bronze_outbox_df,
)

RAW_KAFKA_SCHEMA = StructType(
    [
        StructField("key", StringType(), True),
        StructField("value", StringType(), True),
        StructField("topic", StringType(), True),
        StructField("partition", IntegerType(), True),
        StructField("offset", LongType(), True),
        StructField("timestamp", TimestampType(), True),
    ]
)


@pytest.fixture(scope="session")
def spark():
    return (
        SparkSession.builder.master("local[*]")
        .appName("test_bronze_envelope")
        .getOrCreate()
    )


def _raw_df(spark, value_dict, key="order-1", topic="fullfillment.public.orders"):
    value = json.dumps(value_dict) if value_dict is not None else None
    return spark.createDataFrame([(key, value, topic, 0, 42, None)], RAW_KAFKA_SCHEMA)


def _order_row(**overrides):
    row = {
        "id": "order-1",
        "customer_email": "test@example.com",
        "status": "PENDING",
        "total_amount": None,
        "notes": None,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
        "version": 1,
        "idempotency_key": "abc-123",
    }
    row.update(overrides)
    return row


def _envelope(op, before=None, after=None, lsn=100):
    return {
        "payload": {
            "before": before,
            "after": after,
            "op": op,
            "source": {
                "lsn": lsn,
                "txId": 555,
                "ts_ms": 1700000000000,
                "table": "orders",
            },
            "ts_ms": 1700000000000,
        }
    }


def test_snapshot_op_r_usa_after(spark):
    raw_df = _raw_df(spark, _envelope("r", after=_order_row()))
    row = build_bronze_df(raw_df, ORDER_ROW_SCHEMA).collect()[0]
    assert row["cdc_op"] == "r"
    assert row["id"] == "order-1"
    assert row["after"] is not None
    assert row["before"] is None
    assert row["source_lsn"] == 100


def test_insert_op_c(spark):
    raw_df = _raw_df(spark, _envelope("c", after=_order_row(status="PENDING")))
    row = build_bronze_df(raw_df, ORDER_ROW_SCHEMA).collect()[0]
    assert row["cdc_op"] == "c"
    assert row["status"] == "PENDING"


def test_update_op_u_usa_after_ma_preserva_before(spark):
    raw_df = _raw_df(
        spark,
        _envelope(
            "u",
            before=_order_row(status="PENDING"),
            after=_order_row(status="PAID"),
            lsn=200,
        ),
    )
    row = build_bronze_df(raw_df, ORDER_ROW_SCHEMA).collect()[0]
    assert row["cdc_op"] == "u"
    # data.* (le colonne flat, compatibilità con il comportamento pre-Fase-1)
    # riflette `after`, non `before`
    assert row["status"] == "PAID"
    assert row["before"]["status"] == "PENDING"
    assert row["after"]["status"] == "PAID"
    assert row["source_lsn"] == 200


def test_delete_op_d_usa_before(spark):
    raw_df = _raw_df(
        spark, _envelope("d", before=_order_row(status="PAID"), after=None, lsn=300)
    )
    row = build_bronze_df(raw_df, ORDER_ROW_SCHEMA).collect()[0]
    assert row["cdc_op"] == "d"
    # dopo una delete `after` è null: le colonne flat devono venire da `before`
    assert row["status"] == "PAID"
    assert row["after"] is None
    assert row["source_lsn"] == 300


def test_tombstone_viene_scartato(spark):
    # value=null: un vero tombstone Kafka, non la stringa "null" — stesso
    # comportamento del bug #3 (Fase 0), qui verificato esplicitamente.
    raw_df = _raw_df(spark, None)
    result = build_bronze_df(raw_df, ORDER_ROW_SCHEMA).collect()
    assert result == []


def test_colonna_decimal_viene_decodificata(spark):
    raw_df = _raw_df(spark, _envelope("c", after=_order_row(total_amount="Bnwo")))
    row = build_bronze_df(
        raw_df, ORDER_ROW_SCHEMA, decimal_columns={"total_amount": 4}
    ).collect()[0]
    assert row["total_amount_decoded"] == Decimal("42.5000")


# ── outbox_events, post-EventRouter: forma diversa, funzione diversa ─────────
def test_outbox_evento_instradato_viene_letto(spark):
    domain_event = {"eventId": "evt-1", "orderId": "order-1", "totalPrice": 42.5}
    routed_value = {
        "payload": {
            "payload": json.dumps(domain_event),
            "event_type": "OrderCreated.v1",
            "event_schema_version": 1,
        }
    }
    raw_df = _raw_df(spark, routed_value, key="order-1", topic="outbox.event.Order")
    row = build_bronze_outbox_df(raw_df).collect()[0]
    assert row["event_key"] == "order-1"
    assert row["event_type"] == "OrderCreated.v1"
    assert row["event_schema_version"] == 1
    assert json.loads(row["event_payload"])["orderId"] == "order-1"
