# Bug APERTI di Silver, riprodotti ma non ancora risolti.
# Logica semantica: la fix la scrive Pascal (vedi "Modalità di lavoro" in
# ROADMAP.md). Qui c'è solo la riproduzione del failure mode.
#
# Ogni test è marcato xfail(strict=True, raises=AssertionError):
# - oggi fallisce sull'assert, quindi la CI resta verde ma il bug è visibile
#   nel report (`pytest -rxX` lo elenca come XFAIL);
# - raises=AssertionError: se fallisse per un altro motivo (schema sbagliato,
#   errore Spark) il test risulta FAILED, non XFAIL — così un xfail non
#   nasconde un test rotto;
# - strict=True: quando la fix arriva il test passa, pytest lo segnala come
#   XPASS(strict) e fallisce. È il promemoria per togliere il marker.
#
# Dati di input con la forma REALE di Bronze dopo la Fase 1: `total_amount`
# è la stringa base64 di Debezium (decimal.handling.mode: precise) e il valore
# vero sta in `total_amount_decoded` — non il DoubleType usato dai test di
# test_silver_bugs.py, che per questo non potevano vedere il bug #11.
#
# Esecuzione locale (serve internet al primo avvio per il JAR Delta):
#   pytest spark_apps/tests/test_silver_open_bugs.py -v -rxX -m integration

import base64
import tempfile
from datetime import datetime
from decimal import Decimal

import pytest
from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from spark_apps.cdc_silver import make_process_batch

ORDER_ID = "uuid-order-open"

BRONZE_LIKE_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("customer_email", StringType(), True),
        StructField("status", StringType(), True),
        StructField("total_amount", StringType(), True),
        StructField("total_amount_decoded", DecimalType(19, 4), True),
        StructField("updated_at", TimestampType(), True),
        StructField("version", LongType(), True),
        StructField("cdc_op", StringType(), True),
    ]
)


def debezium_precise(value: Decimal, scale: int = 4) -> str:
    """Codifica come Debezium con decimal.handling.mode: precise: intero non
    scalato, byte big-endian con segno, poi base64."""
    unscaled = int(value.scaleb(scale))
    length = (unscaled.bit_length() + 8) // 8
    return base64.b64encode(unscaled.to_bytes(length, "big", signed=True)).decode()


@pytest.fixture
def evento(spark_delta):
    def factory(status, minute, version, cdc_op, amount=Decimal("199.99")):
        return spark_delta.createDataFrame(
            [
                (
                    ORDER_ID,
                    "mario@gmail.com",
                    status,
                    debezium_precise(amount),
                    amount.quantize(Decimal("0.0001")),
                    datetime(2026, 9, 1, 10, minute),
                    version,
                    cdc_op,
                )
            ],
            BRONZE_LIKE_SCHEMA,
        )

    return factory


@pytest.fixture
def user_df(spark_delta):
    schema = StructType(
        [
            StructField("id", StringType(), True),
            StructField("email", StringType(), True),
            StructField("role", StringType(), True),
            StructField("created_at", LongType(), True),
        ]
    )
    return spark_delta.createDataFrame(
        [("uuid-user-1", "mario@gmail.com", "CUSTOMER", 1700000000)], schema
    )


@pytest.fixture
def item_df(spark_delta):
    schema = StructType(
        [
            StructField("order_id", StringType(), True),
            StructField("items_count", IntegerType(), True),
        ]
    )
    return spark_delta.createDataFrame([], schema)


def silver_rows(spark, tmp):
    silver = spark.read.format("delta").load(f"{tmp}/silver/orders")
    return silver, silver.filter(silver.id == ORDER_ID).collect()


# ── Bug #11 — Silver espone l'importo come stringa base64 ─────────────────────
# Trino (trino/init.sql) dichiara total_amount DOUBLE, i modelli Gold fanno
# SUM(total_amount) e la suite GE valida total_amount: tutti leggono la
# colonna sbagliata. Atteso: in Silver `total_amount` è DECIMAL(19,4) con il
# valore decodificato.
@pytest.mark.integration
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="bug #11 aperto")
def test_bug11_silver_espone_importo_decimale(spark_delta, evento, user_df, item_df):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark_delta, user_df, item_df, tmp)
        process_batch(evento("PENDING", 0, 1, "c"), batch_id=0)
        process_batch(evento("PAID", 5, 2, "u"), batch_id=1)  # passa dalla MERGE

        silver, righe = silver_rows(spark_delta, tmp)
        assert silver.schema["total_amount"].dataType == DecimalType(19, 4)
        assert righe[0]["total_amount"] == Decimal("199.9900")


# ── Bug #12 — primo batch scritto senza MERGE ─────────────────────────────────
# Se Silver non esiste ancora, process_batch fa un write semplice degli
# upsert: nessuna guardia, nessun dedup, delete del batch ignorate.
@pytest.mark.integration
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="bug #12 aperto")
def test_bug12_primo_batch_create_e_update_stesso_id(
    spark_delta, evento, user_df, item_df
):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark_delta, user_df, item_df, tmp)
        batch = evento("PENDING", 0, 1, "c").unionAll(evento("PAID", 5, 2, "u"))
        process_batch(batch, batch_id=0)

        _, righe = silver_rows(spark_delta, tmp)
        assert len(righe) == 1  # oggi: 2 righe con lo stesso id
        assert righe[0]["status"] == "PAID"


@pytest.mark.integration
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="bug #12 aperto")
def test_bug12_primo_batch_create_e_delete_stesso_id(
    spark_delta, evento, user_df, item_df
):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark_delta, user_df, item_df, tmp)
        batch = evento("PENDING", 0, 1, "c").unionAll(evento("PENDING", 5, 2, "d"))
        process_batch(batch, batch_id=0)

        _, righe = silver_rows(spark_delta, tmp)
        assert len(righe) == 0  # oggi: la delete viene ignorata


# ── Bug #13 — eventi di snapshot (op = "r") scartati da Silver ────────────────
# process_batch tiene solo cdc_op in ("c", "u"): le righe lette dallo
# snapshot iniziale di Debezium (op = "r") non arrivano mai in Silver. Tutti
# gli ordini già presenti in Postgres quando si accende la CDC mancano.
@pytest.mark.integration
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="bug #13 aperto")
def test_bug13_evento_di_snapshot_arriva_in_silver(
    spark_delta, evento, user_df, item_df
):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark_delta, user_df, item_df, tmp)
        process_batch(evento("PENDING", 0, 1, "r"), batch_id=0)

        _, righe = silver_rows(spark_delta, tmp)
        assert len(righe) == 1
