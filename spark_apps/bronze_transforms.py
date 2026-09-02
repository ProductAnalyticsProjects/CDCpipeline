import base64
from decimal import Decimal
import logging

from pyspark.sql.functions import (
    col,
    current_timestamp,
    date_format,
    from_json,
    udf,
    when,
)
from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)


def convert_base_to_decimal(column, scale=4):
    try:
        if column is not None:
            decode_bytes = base64.b64decode(column)
            decimal = Decimal(
                int.from_bytes(decode_bytes, byteorder="big", signed=True)
            ).scaleb(-scale)
            return decimal
        else:
            return None
    except Exception as e:
        logger.error(f"Errore di conversione: {e}")
        raise


# Blocco `source` di Debezium (payload.source): stesso per ogni tabella,
# indipendente dallo schema riga. `lsn` è il campo che conta — Fase 2 lo user
# come guardia di ordinamento nel MERGE Silver al posto di updated_at/version
# (vedi docs/adr/002-silver-merge-ordering-guard.md).
SOURCE_SCHEMA = StructType(
    [
        StructField("version", StringType(), True),
        StructField("connector", StringType(), True),
        StructField("name", StringType(), True),
        StructField("ts_ms", LongType(), True),
        StructField("snapshot", StringType(), True),
        StructField("db", StringType(), True),
        StructField("schema", StringType(), True),
        StructField("table", StringType(), True),
        StructField("txId", LongType(), True),
        StructField("lsn", LongType(), True),
        StructField("xmin", LongType(), True),
    ]
)

# Schemi riga (before/after) per le tabelle coperte dal connector Debezium
# `ecommerce-connector` (debezium/connectors/ecommerce.json), presi 1:1 dalle
# migration Flyway in e-commerce/backend/src/main/resources/db/migration/.
ORDER_ROW_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("customer_email", StringType(), True),
        StructField("status", StringType(), True),
        StructField("total_amount", StringType(), True),
        StructField("notes", StringType(), True),
        StructField("created_at", TimestampType(), True),
        StructField("updated_at", TimestampType(), True),
        StructField("version", LongType(), True),
        StructField("idempotency_key", StringType(), True),
    ]
)

USER_ROW_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("email", StringType(), True),
        StructField("password_hash", StringType(), True),
        StructField("role", StringType(), True),
        StructField("created_at", TimestampType(), True),
        StructField("updated_at", TimestampType(), True),
    ]
)

ORDER_ITEM_ROW_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("order_id", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("quantity", IntegerType(), True),
        StructField("unit_price", StringType(), True),
        StructField("subtotal", StringType(), True),
        StructField("created_at", TimestampType(), True),
        StructField("updated_at", TimestampType(), True),
    ]
)


def _debezium_envelope_schema(row_schema):
    return StructType(
        [
            StructField(
                "payload",
                StructType(
                    [
                        StructField("before", row_schema, True),
                        StructField("after", row_schema, True),
                        StructField("op", StringType(), True),  # r=snapshot, c, u, d
                        StructField("source", SOURCE_SCHEMA, True),
                        StructField("ts_ms", LongType(), True),
                    ]
                ),
                True,
            )
        ]
    )


def build_bronze_df(raw_df, row_schema, decimal_columns=None):
    """Parsing puro e testabile dell'envelope Debezium completo per una
    tabella CDC "normale" (orders, users, order_items — non outbox_events,
    che dopo l'EventRouter SMT ha una forma diversa: vedi
    `build_bronze_outbox_df`).

    raw_df: DataFrame Kafka grezzo (key, value, topic, partition, offset,
    timestamp) così come letto da `spark.readStream.format("kafka")`.
    row_schema: StructType della riga Postgres (stessa forma di before/after).
    decimal_columns: {nome_colonna: scale} per le colonne DECIMAL che
    Debezium serializza come bytes base64 con `decimal.handling.mode:
    precise` (es. {"total_amount": 4}) — aggiunge <nome>_decoded, la colonna
    originale resta byte grezzi (stessa scelta del bug #1, Fase 0).

    A differenza della versione pre-Fase-1, non appiattisce subito su
    `after`: prima/dopo restano disponibili come struct, più i metadati
    `source.*` di Debezium (incluso `source_lsn`, promosso a colonna di primo
    livello: Fase 2 lo usa come guardia MERGE) e i metadati nativi del
    messaggio Kafka (key/partition/offset/timestamp) — nessuno di questi era
    catturato prima, e senza sono impossibili ordering, idempotenza e
    replay-from-timestamp (obiettivi 2, 7, 8).
    """
    decimal_columns = decimal_columns or {}
    envelope_schema = _debezium_envelope_schema(row_schema)

    parsed = raw_df.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("kafka_value"),
        col("topic").alias("kafka_topic"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_timestamp"),
    ).select(
        "kafka_key",
        "kafka_value",
        "kafka_topic",
        "kafka_partition",
        "kafka_offset",
        "kafka_timestamp",
        from_json(col("kafka_value"), envelope_schema).alias("debezium"),
    )

    bronze_df = (
        parsed.select(
            when(col("debezium.payload.op") == "d", col("debezium.payload.before"))
            .otherwise(col("debezium.payload.after"))
            .alias("data"),
            col("debezium.payload.op").alias("cdc_op"),
            col("debezium.payload.before").alias("before"),
            col("debezium.payload.after").alias("after"),
            col("debezium.payload.source").alias("source"),
            col("debezium.payload.source.lsn").alias("source_lsn"),
            col("debezium.payload.source.ts_ms").alias("source_ts_ms"),
            col("debezium.payload.source.txId").alias("source_tx_id"),
            "kafka_key",
            "kafka_topic",
            "kafka_partition",
            "kafka_offset",
            "kafka_timestamp",
            "kafka_value",
        )
        .select(
            "data.*",
            "cdc_op",
            "before",
            "after",
            "source",
            "source_lsn",
            "source_ts_ms",
            "source_tx_id",
            "kafka_key",
            "kafka_topic",
            "kafka_partition",
            "kafka_offset",
            "kafka_timestamp",
            "kafka_value",
        )
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn(
            "ingestion_date", date_format(col("ingestion_timestamp"), "yyyy-MM-dd")
        )
        # Tombstone (value=null, cdc_op=null): riga interamente null, va
        # scartata — stessa scelta del bug #3, Fase 0. Il messaggio in sé
        # resta comunque letto (non fallisce), solo la riga risultante non
        # viene scritta in Bronze.
        .na.drop(subset="cdc_op")
    )

    for column_name, scale in decimal_columns.items():
        converter_udf = udf(
            lambda value, s=scale: convert_base_to_decimal(value, s),
            returnType=DecimalType(19, scale),
        )
        bronze_df = bronze_df.withColumn(
            f"{column_name}_decoded", converter_udf(col(column_name))
        )

    return bronze_df


# Schema del messaggio prodotto dall'EventRouter SMT per il topic instradato
# (outbox.event.<aggregatetype>, es. outbox.event.Order — vedi
# debezium/connectors/ecommerce.json). Non è più l'envelope before/after/op:
# l'SMT sostituisce il valore del messaggio con il payload dell'evento di
# dominio, più `type`/`schema_version` spostati in envelope dalla config
# `table.fields.additional.placement`. Nessun prima/dopo, nessuna delete:
# outbox_events è insert-only per costruzione (OutboxService.publish).
OUTBOX_ROUTED_ENVELOPE_SCHEMA = StructType(
    [
        StructField(
            "payload",
            StructType(
                [
                    StructField(
                        "payload", StringType(), True
                    ),  # JSON serializzato del DomainEvent
                    StructField("event_type", StringType(), True),
                    StructField("event_schema_version", IntegerType(), True),
                ]
            ),
            True,
        )
    ]
)


def build_bronze_outbox_df(raw_df):
    """Parsing del topic instradato dall'EventRouter (outbox.event.*), non
    del topic CDC grezzo su outbox_events. Il payload dell'evento di dominio
    resta stringa JSON grezza — la tipizzazione per singolo `event_type` è
    lavoro di Silver (Fase 2), non di questo spike.

    La chiave del messaggio Kafka è `aggregateid` (configurato con
    `table.field.event.key` nel connector): la esponiamo come `event_key`
    per non confonderla con un id Kafka-partition-level qualsiasi.
    """
    envelope_schema = OUTBOX_ROUTED_ENVELOPE_SCHEMA

    parsed = raw_df.select(
        col("key").cast("string").alias("event_key"),
        col("value").cast("string").alias("kafka_value"),
        col("topic").alias("kafka_topic"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_timestamp"),
    ).select(
        "event_key",
        "kafka_value",
        "kafka_topic",
        "kafka_partition",
        "kafka_offset",
        "kafka_timestamp",
        from_json(col("kafka_value"), envelope_schema).alias("routed"),
    )

    return (
        parsed.select(
            col("event_key"),
            col("routed.payload.payload").alias("event_payload"),
            col("routed.payload.event_type").alias("event_type"),
            col("routed.payload.event_schema_version").alias("event_schema_version"),
            "kafka_topic",
            "kafka_partition",
            "kafka_offset",
            "kafka_timestamp",
            "kafka_value",
        )
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn(
            "ingestion_date", date_format(col("ingestion_timestamp"), "yyyy-MM-dd")
        )
        .na.drop(subset="event_type")
    )
