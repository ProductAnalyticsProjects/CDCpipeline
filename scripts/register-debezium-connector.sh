#!/usr/bin/env bash
# Registra (o aggiorna) il connector Debezium per public.orders.
#
# PUT su /connectors/<name>/config invece di POST su /connectors: idempotente,
# puoi rilanciarlo quante volte vuoi. Il vecchio debizium_api.bash usava POST,
# che sul secondo tentativo falliva con 409 Conflict (connector già esistente)
# — un dettaglio che sembra irrilevante finché non serve aggiornare un
# parametro del connector già in esecuzione, il caso più comune in pratica.
#
# Uso: bash scripts/register-debezium-connector.sh
set -euo pipefail

DEBEZIUM_URL="${DEBEZIUM_URL:-http://localhost:8083}"
CONNECTOR_NAME="orders-connector"
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/debezium/connectors/orders.json"

echo "→ Registro/aggiorno $CONNECTOR_NAME su $DEBEZIUM_URL..."

http_status=$(curl -s -o /tmp/debezium_response.json -w "%{http_code}" \
  -X PUT "$DEBEZIUM_URL/connectors/$CONNECTOR_NAME/config" \
  -H "Content-Type: application/json" \
  -d @"$CONFIG_FILE")

cat /tmp/debezium_response.json
echo

# 200 = connector aggiornato (già esisteva), 201 = connector creato la prima volta.
if [ "$http_status" != "200" ] && [ "$http_status" != "201" ]; then
  echo "::error::Registrazione fallita (HTTP $http_status)"
  exit 1
fi

echo "✅ Connector $CONNECTOR_NAME attivo (HTTP $http_status)"
echo "   Stato: $DEBEZIUM_URL/connectors/$CONNECTOR_NAME/status"
