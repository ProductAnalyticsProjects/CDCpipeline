#!/usr/bin/env bash
# Configura la branch protection su `main` per CDCpipeline via GitHub CLI.
# Idempotente: puoi rilanciarlo, sovrascrive semplicemente la configurazione.
#
# Prerequisiti:
#   - GitHub CLI installato e autenticato: `gh auth login`
#   - permessi di admin sul repo ProductAnalyticsProjects/CDCpipeline
#   - i workflow (.github/workflows/ci.yml) devono aver già girato ALMENO
#     UNA VOLTA su main: GitHub registra un "check" come candidato per la
#     required status check solo dopo che è stato eseguito almeno una volta.
#     Fai un push/PR di prova prima di lanciare questo script.
#
# Uso:  bash scripts/setup-branch-protection.sh [owner/repo] [branch]
set -euo pipefail

REPO="${1:-ProductAnalyticsProjects/CDCpipeline}"
BRANCH="${2:-main}"

if ! command -v gh &> /dev/null; then
  echo "::error::GitHub CLI (gh) non trovato. Installa da https://cli.github.com/"
  exit 1
fi

echo "→ Configuro branch protection su $REPO@$BRANCH..."

# Check richiesti = i job del job `ci.yml` che girano SEMPRE (push/PR senza
# path filter). NON includiamo il job `docker` di docker-build.yml: ha un
# `paths:` filter (gira solo se cambiano dockerfile/requirements/spark_apps).
# Un required check che non viene mai creato su una PR che non tocca quei
# file blocca il merge per sempre — è un errore comune, meglio escluderlo.
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "repos/${REPO}/branches/${BRANCH}/protection" \
  -f "required_status_checks[strict]=true" \
  -f "required_status_checks[checks][][context]=Lint & format (pre-commit)" \
  -f "required_status_checks[checks][][context]=Unit tests (pytest + Spark)" \
  -f "required_status_checks[checks][][context]=dbt parse" \
  -f "required_status_checks[checks][][context]=Compose & version consistency" \
  -f "required_status_checks[checks][][context]=Integration (Postgres + Kafka)" \
  -f "required_status_checks[checks][][context]=Airflow DAG integrity" \
  -F "enforce_admins=true" \
  -f "required_pull_request_reviews[required_approving_review_count]=1" \
  -f "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -F "restrictions=null" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false" \
  -F "required_linear_history=false"

echo "✅ Branch protection attiva su $BRANCH:"
echo "   - 6 check richiesti verdi prima del merge"
echo "   - 1 review approvata richiesta, review 'stale' scartate a nuovi commit"
echo "   - niente force-push, niente cancellazione del branch"
echo "   - enforce_admins=true: la regola vale anche per te come admin del repo"
echo
echo "Verifica in: https://github.com/${REPO}/settings/branches"
