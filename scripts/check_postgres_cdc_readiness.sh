#!/usr/bin/env bash
# Verifica che il Postgres di test sia pronto per la CDC via Debezium/pgoutput:
#   1. wal_level=logical è impostato (Debezium usa il replication protocol
#      logico; senza questo, la connessione al connettore fallisce a runtime,
#      SILENZIOSAMENTE fino al primo tentativo di creare uno slot)
#   2. init-db/init.sql si applica senza errori
#   3. una publication + uno slot di replica logica si creano davvero
#      (esattamente quello che fa Debezium alla prima connessione)
#
# Usato dal job `integration-test` in ci.yml. Il Postgres ufficiale non
# accetta `-c wal_level=logical` via variabili d'ambiente (solo via comando,
# che i service container di GitHub Actions non supportano), quindi lo
# impostiamo a mano nel postgresql.conf e riavviamo il container.
set -euo pipefail

PG_USER="${POSTGRES_USER:-ci}"
PG_DB="${POSTGRES_DB:-ci_test}"

echo "→ Individuo il container Postgres del service..."
PG_CID=$(docker ps -q --filter ancestor=postgres:16 | head -1)
if [ -z "$PG_CID" ]; then
  echo "::error::Container Postgres non trovato (atteso image postgres:16)"
  exit 1
fi
echo "  container: $PG_CID"

echo "→ Imposto wal_level=logical e riavvio..."
docker exec "$PG_CID" bash -c 'echo "wal_level = logical" >> /var/lib/postgresql/data/postgresql.conf'
docker restart "$PG_CID" > /dev/null

echo "→ Attendo che Postgres torni pronto dopo il riavvio..."
for i in $(seq 1 30); do
  if docker exec "$PG_CID" pg_isready -U "$PG_USER" -d "$PG_DB" > /dev/null 2>&1; then
    echo "  pronto dopo ${i}0 tentativi"
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "::error::Postgres non è tornato pronto dopo il riavvio"
    exit 1
  fi
done

actual_wal_level=$(docker exec "$PG_CID" psql -U "$PG_USER" -d "$PG_DB" -tAc "SHOW wal_level;")
echo "  wal_level=$actual_wal_level"
if [ "$actual_wal_level" != "logical" ]; then
  echo "::error::wal_level è '$actual_wal_level', atteso 'logical'"
  exit 1
fi

echo "→ Applico init-db/init.sql..."
docker exec -i "$PG_CID" psql -U "$PG_USER" -d "$PG_DB" < init-db/init.sql

echo "→ Verifico che il database 'ecommerce' sia stato creato..."
created=$(docker exec "$PG_CID" psql -U "$PG_USER" -d "$PG_DB" -tAc \
  "SELECT 1 FROM pg_database WHERE datname='ecommerce';")
if [ "$created" != "1" ]; then
  echo "::error::init-db/init.sql non ha creato il database 'ecommerce'"
  exit 1
fi

echo "→ Simulo esattamente quello che fa Debezium alla prima connessione..."
docker exec "$PG_CID" psql -U "$PG_USER" -d ecommerce -c \
  "CREATE TABLE IF NOT EXISTS public.orders (id text PRIMARY KEY, status text);"
docker exec "$PG_CID" psql -U "$PG_USER" -d ecommerce -c \
  "DROP PUBLICATION IF EXISTS dbz_ci_test; CREATE PUBLICATION dbz_ci_test FOR TABLE public.orders;"
docker exec "$PG_CID" psql -U "$PG_USER" -d ecommerce -c \
  "SELECT pg_create_logical_replication_slot('dbz_ci_test_slot', 'pgoutput');"
docker exec "$PG_CID" psql -U "$PG_USER" -d ecommerce -c \
  "SELECT pg_drop_replication_slot('dbz_ci_test_slot');"

echo "✅ Postgres pronto per CDC: wal_level logical, init.sql applicato, publication + slot funzionanti"
