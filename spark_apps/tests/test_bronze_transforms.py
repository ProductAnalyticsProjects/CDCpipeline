import base64
from decimal import Decimal

from spark_apps.bronze_transforms import convert_base_to_decimal


def test_valore_reale_osservato_su_kafka():
    """'Bnwo' è il valore base64 osservato davvero sul topic Kafka per un
    total_amount di 42.50 (scale=4) — vedi docs/adr/001-debezium-connector-config.md."""
    assert convert_base_to_decimal("Bnwo") == Decimal("42.5000")


def test_valore_null_ritorna_none():
    assert convert_base_to_decimal(None) is None


def test_valore_negativo_rispetta_il_segno():
    # Costruito qui, non hardcoded: prende un valore negativo noto (-42.50,
    # scale=4), lo codifica esattamente come farebbe Debezium (big-endian,
    # two's complement, unscaled = -425000), e verifica che decodificarlo
    # torni al valore di partenza. Se `signed=True` mancasse nella funzione,
    # questo test fallisce.
    unscaled = -425000
    encoded_bytes = unscaled.to_bytes(3, byteorder="big", signed=True)
    encoded_base64 = base64.b64encode(encoded_bytes).decode()

    assert convert_base_to_decimal(encoded_base64) == Decimal("-42.5000")
