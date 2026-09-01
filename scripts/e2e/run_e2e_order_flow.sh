#!/usr/bin/env bash
# Flusso e2e minimo per generare UN vero ordine attraverso l'API del backend:
# login admin (seedato solo con SPRING_PROFILES_ACTIVE=docker,local — vedi
# docker-compose.ci.yml) → crea prodotto → aggiunge stock → registra/logga
# un customer → crea l'ordine. Stessa sequenza di e-commerce/backend/test.http,
# automatizzata per la CI.
#
# Stampa su stdout una sola riga JSON con i dati che il passo successivo
# (lettura di Bronze) usa per trovare la riga giusta: {"customer_email": "..."}
#
# Uso: bash scripts/e2e/run_e2e_order_flow.sh
set -euo pipefail

BASE_URL="${BACKEND_BASE_URL:-http://localhost:8085/api/v1}"
WAREHOUSE_ID="00000000-0000-0000-0000-000000000001"

# Email univoca per run: evita collisioni se il job gira più volte di fila
# (customer già registrato) e dà al passo successivo un valore certo su cui
# filtrare in Bronze, invece di indovinare "l'ultima riga".
RUN_ID="${GITHUB_RUN_ID:-$(date +%s)}"
CUSTOMER_EMAIL="e2e-${RUN_ID}@test.local"
CUSTOMER_PASSWORD="e2e-password-123"

log() { echo "→ $*" >&2; }

# --- 1. Admin: login (seedato da DataInitializer, richiede il profilo "local") ---
log "Login admin..."
admin_login_response=$(curl -sf -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin123"}')
ADMIN_TOKEN=$(echo "$admin_login_response" | jq -r '.token')

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
  echo "::error::Login admin fallito — l'utente seedato esiste? SPRING_PROFILES_ACTIVE include 'local'?" >&2
  echo "$admin_login_response" >&2
  exit 1
fi

# --- 2. Admin: crea un prodotto ---
log "Creo un prodotto..."
product_response=$(curl -sf -X POST "$BASE_URL/products" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"name\":\"E2E test product\",\"description\":\"Creato dal job e2e-test\",\"basePrice\":9.99,\"sku\":\"E2E-${RUN_ID}\"}")
PRODUCT_ID=$(echo "$product_response" | jq -r '.id')

if [ -z "$PRODUCT_ID" ] || [ "$PRODUCT_ID" = "null" ]; then
  echo "::error::Creazione prodotto fallita" >&2
  echo "$product_response" >&2
  exit 1
fi

# --- 3. Admin: aggiunge stock sul warehouse di default ---
log "Aggiungo stock per il prodotto $PRODUCT_ID..."
curl -sf -X POST "$BASE_URL/inventory" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"productId\":\"$PRODUCT_ID\",\"warehouseId\":\"$WAREHOUSE_ID\",\"quantity\":100}" \
  > /dev/null

# --- 4. Customer: registrazione + login ---
log "Registro il customer $CUSTOMER_EMAIL..."
curl -sf -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$CUSTOMER_EMAIL\",\"password\":\"$CUSTOMER_PASSWORD\"}" \
  > /dev/null

customer_login_response=$(curl -sf -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$CUSTOMER_EMAIL\",\"password\":\"$CUSTOMER_PASSWORD\"}")
CUSTOMER_TOKEN=$(echo "$customer_login_response" | jq -r '.token')

if [ -z "$CUSTOMER_TOKEN" ] || [ "$CUSTOMER_TOKEN" = "null" ]; then
  echo "::error::Login customer fallito" >&2
  echo "$customer_login_response" >&2
  exit 1
fi

# --- 5. Customer: crea l'ordine — questo è l'evento che deve arrivare in Bronze ---
log "Creo l'ordine..."
order_response=$(curl -sf -X POST "$BASE_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d "{\"customerEmail\":\"$CUSTOMER_EMAIL\",\"items\":[{\"productId\":\"$PRODUCT_ID\",\"quantity\":2}],\"notes\":\"e2e-test\"}")
ORDER_ID=$(echo "$order_response" | jq -r '.id')

if [ -z "$ORDER_ID" ] || [ "$ORDER_ID" = "null" ]; then
  echo "::error::Creazione ordine fallita" >&2
  echo "$order_response" >&2
  exit 1
fi

log "✅ Ordine $ORDER_ID creato per $CUSTOMER_EMAIL"

# Output macchina-leggibile per il passo successivo (lettura Bronze).
jq -n --arg email "$CUSTOMER_EMAIL" --arg order_id "$ORDER_ID" \
  '{customer_email: $email, order_id: $order_id}'
