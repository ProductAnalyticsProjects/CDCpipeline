import base64
from decimal import Decimal
import logging

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
