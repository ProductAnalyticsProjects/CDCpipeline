#!/usr/bin/env bash
# Registra (o aggiorna) il connector Debezium per l'intero schema `ecommerce`
# (orders, users, order_items, outbox_events — vedi ROADMAP.md, Fase 1).
#
# PUT su /connectors/<name>/config invece di POST su /connectors: idempotente,
# puoi rilanciarlo quante volte vuoi. Il vecchio debizium_api.bash usava POST,
# che sul secondo tentativo falliva con 409 Conflict (connector già esistente)
# — un dettaglio che sembra irrilevante finché non serve aggiornare un
# parametro del connector già in esecuzione, il caso più comune in pratica.
#
# NOTA per chi ha già un ambiente da prima della Fase 1, due cose:
# 1. Il connector si chiama ora `ecommerce-connector` (prima `orders-connector`):
#    un PUT con nome nuovo REGISTRA un secondo connector, non sostituisce il
#    vecchio — che resta attivo e conteso sullo stesso `slot.name`.
# 2. `publication.name` non cambia (resta `debezium_orders_publication`), e
#    con `publication.autocreate.mode=filtered` Debezium NON altera da solo
#    una publication che esiste già — se è stata creata quando
#    `table.include.list` copriva solo `public.orders`, questo PUT da solo
#    non basta a far arrivare users/order_items/outbox_events.
# In entrambi i casi la via pulita è `docker compose down -v` (stesso reset
# già richiesto in Fase 0.1) prima di ri-registrare.
#
# Uso: bash scripts/register-debezium-connector.sh
set -euo pipefail

DEBEZIUM_URL="${DEBEZIUM_URL:-http://localhost:8083}"
CONNECTOR_NAME="ecommerce-connector"
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/debezium/connectors/ecommerce.json"

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
