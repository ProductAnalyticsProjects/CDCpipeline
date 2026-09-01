"""Verifica e2e: la riga dell'ordine appena creato è arrivata in Bronze con
importi e timestamp non-null (criterio di uscita di Fase 0, ROADMAP.md).

Va eseguito DENTRO al container spark-master (stessa immagine di
cdc_bronze.py/cdc_silver.py: s3a/Delta/hadoop-aws già configurati) — non
gira sul runner CI nudo, che non ha questi jar. Il job e2e-test lo copia nel
container e lo lancia con `python3`, non `spark-submit` (basta client mode
locale per una singola lettura batch, non serve il cluster).

Uso: python3 check_bronze_row.py --email <customer_email>
"""

import argparse
import os
import sys

from spark_apps.cdc_silver import create_spark_session

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
BUCKET = "lakehouse"

CAMPI_DA_VERIFICARE = ["total_amount_decoded", "created_at", "updated_at"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="customer_email dell'ordine e2e")
    args = parser.parse_args()

    spark = create_spark_session(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET)
    bronze = spark.read.format("delta").load(f"s3a://{BUCKET}/bronze/orders")

    righe = bronze.filter(bronze.customer_email == args.email).collect()

    if not righe:
        print(f"❌ Nessuna riga in Bronze per customer_email={args.email}")
        sys.exit(1)

    riga = righe[-1]  # l'ultima, se per qualche motivo ce n'è più di una
    print(f"Riga trovata: {riga.asDict()}")

    campi_null = [campo for campo in CAMPI_DA_VERIFICARE if riga[campo] is None]
    if campi_null:
        print(f"❌ Campi null che non dovrebbero esserlo: {campi_null}")
        sys.exit(1)

    print("✅ Riga in Bronze trovata, nessun campo critico è null")


if __name__ == "__main__":
    main()
