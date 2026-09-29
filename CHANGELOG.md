# Changelog

Tutte le modifiche rilevanti di questo progetto, in ordine cronologico
inverso. Formato basato su [Keep a Changelog](https://keepachangelog.com/it/1.1.0/).
Ogni fase chiusa di [ROADMAP.md](ROADMAP.md) diventa un tag semver e una
sezione qui sotto.

## [Unreleased]

### Added
- `scripts/e2e/check_silver_row.py` e verifica Silver nel job `e2e-test`: la riga dell'ordine e2e deve arrivare anche in Silver, non solo in Bronze
- Step CI "Silver su Delta reale": i test `integration` fuori da `tests/integration/` (guardie di ordinamento, enrichment) prima non giravano in nessun job
- `spark_apps/tests/test_silver_open_bugs.py`: bug aperti #11 (importo base64 in Silver), #12 (primo batch senza MERGE), #13 (snapshot `op=r` scartati), marcati `xfail(strict=True)`
- Fixture `spark_delta` condivisa in `spark_apps/tests/conftest.py`, marker `integration` registrato in `pytest.ini`
- `LICENSE` (MIT), `.gitattributes`, sezione Contributi nel README
- `.github/pull_request_template.md`, `.github/dependabot.yml`
- Gate pre-commit: gitleaks, conventional-pre-commit, hadolint, shellcheck, sqlfluff
- `permissions: contents: read` e `concurrency` su entrambi i workflow GitHub Actions
- `docs/git-workflow.md`, `docs/ci-cd.md`, `docs/learning-log.md`, `docs/learning/01-kafka-fundamentals.md`
- `scripts/backup-local-untracked.sh`

### Changed
- `cdc_silver.py`: URL JDBC costruito da `POSTGRES_HOST`/`POSTGRES_DB` (puntava ancora al vecchio DB `inventory`); `POSTGRES_DB` passato a `spark-master` e `spark-worker` nel compose
- `cdc_bronze.py`, `cdc_silver.py`: un errore dello stream viene loggato e rilanciato, invece di far uscire il processo con codice 0
- `vacuum.py`: solo tabelle esistenti scritte da Spark (rimosso il path `gold/orders`, mai esistito), retention esplicita, niente override di `retentionDurationCheck`, exit code 1 se un VACUUM fallisce; cartella `maintenence/` rinominata `maintenance/` (`start_vacuum.bash` puntava già al nome corretto)
- `e2e-test`: Silver avviato dopo la verifica di Bronze
- `test_silver_enrichment.py`: dati dei test su Delta con `updated_at`/`version` (dopo la guardia di ordinamento la delete falliva per colonna inesistente)
- DAG `cdc_batch_pipeline`: `dbt build` separato in `dbt_run_gold` e `dbt_test_gold`
- README: claim exactly-once ristretto a Kafka→Bronze, nome del file del connector (`ecommerce.json`), tabelle catturate
- ADR 001: stato dei bug #1-#3, spiegazione dell'heartbeat corretta (tabelle catturate inattive, non DB inattivo)
- Immagini Docker (`minio`, `grafana`, `kafka-ui`, `pgadmin4`, `prometheus`, `mc`) pinnate a digest specifici invece di `:latest`
- `scripts/setup-branch-protection.sh`: `required_approving_review_count` da 1 a 0 (con `enforce_admins=true` bloccava il merge su un repo a maintainer singolo), `required_linear_history` a `true`
- `CICD_SETUP.md` (doc di handoff) sostituito da `docs/ci-cd.md`

### Removed
- 740 blob / 561.7 MB di dati di runtime (`data/`: Kafka, Postgres WAL, Zookeeper) committati per errore, rimossi dall'intera history
- Branch `dev` (stale da mesi), archiviato come tag `archive/dev` prima della cancellazione dal remote
