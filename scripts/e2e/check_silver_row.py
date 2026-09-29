"""Verifica e2e: l'ordine appena creato è arrivato anche in Silver.

Stesso contesto di check_bronze_row.py: va eseguito DENTRO al container
spark-master (s3a/Delta/hadoop-aws già configurati) con `python3`, non
`spark-submit`.

Controlla solo che la riga esista con i campi chiave valorizzati. Non
controlla l'importo (in Silver `total_amount` è ancora la stringa base64 di
Debezium, il valore vero sta in `total_amount_decoded` — bug aperto, vedi
spark_apps/tests/test_silver_open_bugs.py) né l'unicità per id (primo batch
senza MERGE, stesso file di test): quei due casi sono coperti da test
dedicati marcati xfail, così questo check non diventa rosso per un bug già
noto e tracciato.

Uso: python3 check_silver_row.py --email <customer_email>
"""

import argparse
import os
import sys

from spark_apps.cdc_silver import create_spark_session

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET = os.environ["MINIO_SECRET_KEY"]
BUCKET = "lakehouse"

CAMPI_DA_VERIFICARE = ["id", "status", "created_at"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="customer_email dell'ordine e2e")
    args = parser.parse_args()

    spark = create_spark_session(MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET)
    silver_path = f"s3a://{BUCKET}/silver/orders"

    # Import tardivo: DeltaTable richiede la SparkSession già creata.
    from delta.tables import DeltaTable

    if not DeltaTable.isDeltaTable(spark, silver_path):
        print(f"❌ La tabella Silver non esiste ancora: {silver_path}")
        sys.exit(1)

    silver = spark.read.format("delta").load(silver_path)
    righe = silver.filter(silver.customer_email == args.email).collect()

    if not righe:
        print(f"❌ Nessuna riga in Silver per customer_email={args.email}")
        sys.exit(1)

    riga = righe[-1]
    print(f"Riga trovata: {riga.asDict()}")

    campi_null = [campo for campo in CAMPI_DA_VERIFICARE if riga[campo] is None]
    if campi_null:
        print(f"❌ Campi null che non dovrebbero esserlo: {campi_null}")
        sys.exit(1)

    print("✅ Riga in Silver trovata, nessun campo chiave è null")


if __name__ == "__main__":
    main()
