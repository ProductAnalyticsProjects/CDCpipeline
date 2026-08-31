# Changelog

Tutte le modifiche rilevanti di questo progetto, in ordine cronologico
inverso. Formato basato su [Keep a Changelog](https://keepachangelog.com/it/1.1.0/).
Ogni fase chiusa di [ROADMAP.md](ROADMAP.md) diventa un tag semver e una
sezione qui sotto.

## [Unreleased]

### Added
- `LICENSE` (MIT), `.gitattributes`, sezione Contributi nel README
- `.github/pull_request_template.md`, `.github/dependabot.yml`
- Gate pre-commit: gitleaks, conventional-pre-commit, hadolint, shellcheck, sqlfluff
- `permissions: contents: read` e `concurrency` su entrambi i workflow GitHub Actions
- `docs/git-workflow.md`, `docs/ci-cd.md`, `docs/learning-log.md`, `docs/learning/01-kafka-fundamentals.md`
- `scripts/backup-local-untracked.sh`

### Changed
- Immagini Docker (`minio`, `grafana`, `kafka-ui`, `pgadmin4`, `prometheus`, `mc`) pinnate a digest specifici invece di `:latest`
- `scripts/setup-branch-protection.sh`: `required_approving_review_count` da 1 a 0 (con `enforce_admins=true` bloccava il merge su un repo a maintainer singolo), `required_linear_history` a `true`
- `CICD_SETUP.md` (doc di handoff) sostituito da `docs/ci-cd.md`

### Removed
- 740 blob / 561.7 MB di dati di runtime (`data/`: Kafka, Postgres WAL, Zookeeper) committati per errore, rimossi dall'intera history
- Branch `dev` (stale da mesi), archiviato come tag `archive/dev` prima della cancellazione dal remote
