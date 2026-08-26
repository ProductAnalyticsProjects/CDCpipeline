#!/usr/bin/env bash
# Backup locale dei file NON tracciati da git che non sono cache rigenerabile
# (.venv, __pycache__, dbt_packages, node_modules, data/, ecc. non servono:
# si ricreano da soli).
#
# Perché serve: git protegge tutto ciò che è committato tramite il remote
# GitHub — quella è la vera copia di sicurezza, fuori macchina. Ma i file
# in questa lista sono deliberatamente in .gitignore, quindi esistono SOLO
# su questa macchina. Se lavori in una cartella sincronizzata da OneDrive/
# Dropbox/Google Drive, la sincronizzazione può sembrare un backup ma non
# lo è (rispecchia anche le cancellazioni per errore), e su questo repo
# specifico OneDrive ha già causato timeout e uno stato di history
# incoerente durante un git-filter-repo (vedi docs/git-workflow.md).
#
# Uso: bash scripts/backup-local-untracked.sh
# Destinazione: ~/Backups/<nome-repo>-local-<timestamp>.tar.gz
#
# --no-xattrs: su file dentro una cartella OneDrive, `cp`/`tar` che provano
# a copiare anche gli extended attribute possono fallire con
# "fcopyfile failed: Operation timed out" anche su file di poche centinaia
# di byte — bug osservato in pratica su questo Mac. Escludere gli xattr
# aggira il problema senza perdere contenuto.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

REPO_NAME="$(basename "$REPO_ROOT")"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
DEST_DIR="$HOME/Backups"
DEST_FILE="$DEST_DIR/${REPO_NAME}-local-${TIMESTAMP}.tar.gz"

# Percorsi non tracciati e non rigenerabili. Aggiungi qui se ne crei altri
# (es. un nuovo script di esperimento in spark_apps/, un nuovo .env.*).
PATHS=(
  .env
  .vscode
  test
  spark_apps/esercizio_a.py
  spark_apps/esercizio_b.py
  spark_apps/utenti.json
  spark_apps/cdc_dump.json
)

echo "→ Verifico quali percorsi esistono..."
EXISTING=()
for p in "${PATHS[@]}"; do
  if [ -e "$p" ]; then
    EXISTING+=("$p")
  else
    echo "  (assente, salto: $p)"
  fi
done

if [ "${#EXISTING[@]}" -eq 0 ]; then
  echo "::error::Nessuno dei percorsi attesi esiste — niente da salvare."
  exit 1
fi

mkdir -p "$DEST_DIR"

echo "→ Creo l'archivio..."
tar -czf "$DEST_FILE" --no-xattrs "${EXISTING[@]}"

echo "✅ Backup creato: $DEST_FILE ($(du -h "$DEST_FILE" | cut -f1))"
echo "   Contenuto:"
for p in "${EXISTING[@]}"; do
  echo "   - $p"
done
