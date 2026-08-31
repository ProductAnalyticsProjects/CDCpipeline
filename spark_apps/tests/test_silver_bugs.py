# Riproduzione dei bug #4, #5, #6 — ROADMAP.md, Fase 0 / 0.3.
# Logica semantica: la scrive Pascal (vedi "Modalità di lavoro" in ROADMAP.md).
# Qui c'è solo l'impalcatura per riprodurre il failure mode con process_batch,
# senza dover passare da un replay Kafka vero (che arriva in Fase 5).
#
# ATTENZIONE prima di scrivere i dati di input: Bronze oggi NON porta alcun
# source_lsn / offset Kafka (arriva in Fase 1 — vedi ROADMAP.md, "Bronze come
# vero event store"). L'unico ordine ricavabile oggi viene dal payload
# applicativo: `updated_at` e `version` in order_schema (cdc_bronze.py).
# Per i delete la situazione è peggiore: `op="d"` porta `before`, cioè lo
# stato PRIMA della cancellazione — non esiste un updated_at "del delete".
#
# Predici per iscritto l'esito ATTUALE (sbagliato) di ogni test prima di
# lanciarlo.
#
# Esecuzione locale (non serve Docker — la fixture spark usa
# configure_spark_with_delta_pip, che scarica il JAR Delta da Maven al primo
# avvio: serve internet la prima volta):
#   pytest spark_apps/tests/test_silver_bugs.py -v -m integration

import pytest
import tempfile
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
    DoubleType,
    LongType,
    IntegerType,
)
from spark_apps.cdc_silver import make_process_batch


def read_last_row(spark, tmp, only_last=True):
    result = spark.read.format("delta").load(f"{tmp}/silver/orders")

    if only_last:
        row = result.filter(result.id == "uuid-order-x").first()
    else:
        row = result.filter(result.id == "uuid-order-x")
    return row


@pytest.fixture(scope="session")
def spark():
    # A differenza della fixture "spark" di test_silver_enrichment.py, qui serve
    # il JAR Delta vero (process_batch scrive/fa MERGE su Delta): in Docker
    # arriva pre-installato (dockerfile:5), in locale configure_spark_with_delta_pip
    # lo scarica da Maven al primo avvio (richiede internet).
    # extensions/catalog: senza questi due, .write.format("delta") funziona ma
    # il MERGE no (serve l'estensione SQL registrata) — stessi due config di
    # create_spark_session() in cdc_silver.py:16-20, ma vanno messi PRIMA di
    # configure_spark_with_delta_pip, che da solo aggiunge solo il jar.
    builder = (
        SparkSession.builder.master("local[*]")
        .appName("test_silver_bugs")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


@pytest.fixture
def order_schema():
    return StructType(
        [
            StructField("id", StringType(), True),
            StructField("customer_email", StringType(), True),
            StructField("status", StringType(), True),
            StructField("total_amount", DoubleType(), True),
            StructField("updated_at", LongType(), True),
            StructField("version", LongType(), True),
            StructField("cdc_op", StringType(), True),
        ]
    )


@pytest.fixture
def create_dataframe(spark, order_schema):
    def factory(
        status: str,
        updated_at: int,
        versione: int,
        cdc_op: str,
        customer_email="test",
        total_amount=1000.0,
        id="uuid-order-x",
    ):
        df = spark.createDataFrame(
            [(id, customer_email, status, total_amount, updated_at, versione, cdc_op)],
            order_schema,
        )
        return df

    return factory


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
    return spark.createDataFrame([], schema)


# ── Bug #4 — cdc_silver.py:57, whenMatchedUpdateAll() senza guardia ──────────
# Un replay (o un batch fuori ordine) porta un update VECCHIO dopo uno NUOVO:
# whenMatchedUpdateAll() non confronta niente, vince sempre l'ultimo arrivato.
@pytest.mark.integration
def test_bug4_update_vecchio_sovrascrive_stato_piu_recente(
    spark, create_dataframe, user_df, item_df
):
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark, user_df, item_df, tmp)

        # 1. batch_0: stato iniziale dell'ordine
        # 2. batch_1: lo stesso id avanza a uno stato più recente (updated_at/version più alti)
        # 3. batch_2: un REPLAY ripropone un update con updated_at/version
        #    intermedio tra batch_0 e batch_1 — ma arriva per ULTIMO
        # Predizione scritta: quale stato leggi in Silver dopo batch_2, oggi?
        batch_0 = create_dataframe(
            status="pending",
            updated_at=1,
            versione=1,
            cdc_op="c",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        batch_1 = create_dataframe(
            status="complete",
            updated_at=3,
            versione=3,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        batch_2 = create_dataframe(
            status="processing",
            updated_at=2,
            versione=2,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        batch_3 = create_dataframe(
            status="processing",
            updated_at=3,
            versione=5,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        batch_4 = create_dataframe(
            status="delete",
            updated_at=None,
            versione=6,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        batch_5 = create_dataframe(
            status="create",
            updated_at=7,
            versione=6,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )

        process_batch(batch_0, batch_id=1)
        process_batch(batch_1, batch_id=2)
        process_batch(batch_2, batch_id=3)
        row_1 = read_last_row(spark, tmp)
        assert row_1["status"] == "complete"

        process_batch(batch_3, batch_id=4)
        row_2 = read_last_row(spark, tmp)
        assert row_2["status"] == "processing"

        process_batch(batch_4, batch_id=5)
        row_3 = read_last_row(spark, tmp)
        assert row_3["status"] == "delete"

        process_batch(batch_5, batch_id=6)
        row_4 = read_last_row(spark, tmp)
        assert row_4["status"] == "create"


# ── Bug #5 — cdc_silver.py:65, delete senza guardia di ordinamento ───────────
# Fix (vedi ADR 003): la delete guadagna la STESSA guardia updated_at/version
# dell'upsert (bug #4), con l'ordine upsert-poi-delete invariato. Questo
# copre sia i replay TRA batch diversi sia una singola coppia d+c nello
# STESSO batch: la seconda MERGE valuta la guardia contro lo stato di Silver
# già aggiornato dalla prima, quindi converge sull'evento più recente a
# prescindere da quale dei due arrivi "per primo" nel batch_df.
# Limite residuo, non coperto: 3+ eventi per lo stesso id nello stesso
# batch — lì Delta fallisce con un errore ("multiple source rows matched"),
# non un risultato silenziosamente sbagliato. Richiede il dedup per chiave
# di Fase 2 (row_number() + MERGE unica), insieme al soft delete che
# cambierà comunque la forma di questa MERGE.


@pytest.mark.integration
def test_bug5_delete_vecchia_non_cancella_stato_ricreato_dopo(
    spark, create_dataframe, user_df, item_df
):
    # Fix: un delete "stale" (replay) che arriva in un batch SUCCESSIVO a
    # quando l'ordine è stato ricreato non deve più cancellarlo.
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark, user_df, item_df, tmp)

        # 1. batch_0: crea l'ordine
        batch_0 = create_dataframe(
            status="create",
            updated_at=7,
            versione=7,
            cdc_op="c",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        process_batch(batch_0, batch_id=0)

        # 2. batch_1: un REPLAY ripropone una delete vecchia (updated_at/version
        #    più bassi di batch_0) — deve essere respinta dalla guardia
        # Predizione scritta: l'ordine è ancora in Silver dopo batch_1?
        batch_1 = create_dataframe(
            status="create",
            updated_at=2,
            versione=2,
            cdc_op="d",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )
        process_batch(batch_1, batch_id=1)

        row = read_last_row(spark, tmp)
        assert row["status"] == "create"


@pytest.mark.integration
def test_bug5_ultimo_stato_in_silver(spark, create_dataframe, user_df, item_df):
    # Conferma (non più un limite noto): con l'ordine upsert-poi-delete e la
    # stessa guardia su entrambe le MERGE, una coppia d+c per lo stesso id
    # nello stesso batch converge sull'evento con updated_at/version più
    # alto, indipendentemente da quale dei due sia scritto per primo nel
    # batch_df. batch_1 verifica la direzione delete-poi-create (vince il
    # create, più recente); batch_2 verifica update-poi-delete (vince la
    # delete, più recente).
    with tempfile.TemporaryDirectory() as tmp:
        process_batch = make_process_batch(spark, user_df, item_df, tmp)

        batch_0 = create_dataframe(
            status="create",
            updated_at=0,
            versione=0,
            cdc_op="c",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )

        batch_1 = create_dataframe(
            status="delete",
            updated_at=2,
            versione=2,
            cdc_op="d",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        ).unionAll(
            create_dataframe(
                status="create",
                updated_at=3,
                versione=3,
                cdc_op="c",
                customer_email="mario@gmail.com",
                total_amount=100.0,
            )
        )

        batch_2 = create_dataframe(
            status="update",
            updated_at=3,
            versione=3,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        ).unionAll(
            create_dataframe(
                status="delete",
                updated_at=4,
                versione=4,
                cdc_op="d",
                customer_email="mario@gmail.com",
                total_amount=100.0,
            )
        )
        process_batch(batch_0, batch_id=0)
        process_batch(batch_1, batch_id=1)
        row = read_last_row(spark, tmp, only_last=False).collect()
        assert row[0]["status"] == "create"

        process_batch(batch_2, batch_id=2)
        row = read_last_row(spark, tmp, only_last=False).collect()
        assert len(row) == 0


# ── Bug #6 — cdc_silver.py:94, user_df/item_df cachati una volta all'avvio ──
# Un utente creato DOPO l'avvio dello stream Silver non esiste nel user_df
# catturato nella closure di process_batch: l'enrichment resta null per sempre,
# non solo finché la cache scade (non scade mai).
@pytest.mark.integration
def test_bug6_utente_registrato_dopo_lo_start_non_arriva_mai_in_enrichment(
    spark, create_dataframe, item_df
):
    with tempfile.TemporaryDirectory() as tmp:
        # user_df "al momento dello start": vuoto o
        # con altri utenti — il punto è che NON contiene l'utente del batch.
        schema_utenti = StructType(
            [
                StructField("id", StringType(), True),
                StructField("email", StringType(), True),
                StructField("role", StringType(), True),
                StructField("created_at", LongType(), True),
            ]
        )
        user_path = f"{tmp}/users"
        spark.createDataFrame([], schema_utenti).write.format("delta").save(user_path)
        user_df_allo_start = spark.read.format("delta").load(user_path)
        process_batch = make_process_batch(spark, user_df_allo_start, item_df, tmp)

        batch_0 = create_dataframe(
            status="create",
            updated_at=3,
            versione=3,
            cdc_op="c",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )

        # Un ordine del "nuovo" utente, arrivato in un batch qualsiasi DOPO
        # lo start. Predizione scritta: user_email nel risultato è null?
        # E se aspetti un'ora prima di mandare il batch, cambia qualcosa?
        process_batch(batch_0, batch_id=0)
        row = read_last_row(spark, tmp)
        assert row["user_email"] is None

        user_aggiornato = spark.createDataFrame(
            [("user-x", "mario@gmail.com", "user", 1231231)], schema_utenti
        )

        user_aggiornato.write.format("delta").mode("append").save(user_path)
        batch_1 = create_dataframe(
            status="update",
            updated_at=4,
            versione=4,
            cdc_op="u",
            customer_email="mario@gmail.com",
            total_amount=100.0,
        )

        process_batch(batch_1, batch_id=1)
        row = read_last_row(spark, tmp)
        assert row["user_email"] == "mario@gmail.com"
