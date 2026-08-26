# CI/CD — setup e razionale

Pipeline GitHub Actions per il progetto CDC: feedback veloce senza dover
accendere l'intero stack, più orchestrazione Airflow del layer gold e
branch protection su `main`. Per lo stato del flusso git (PR, branch
protection, gate pre-commit, versionamento) vedi [git-workflow.md](git-workflow.md).

## Cosa fa `ci.yml` (6 job)

| Job | Cosa verifica | Perché così |
|-----|---------------|-------------|
| **lint** | ruff + ruff-format + gitleaks + hadolint + shellcheck + sqlfluff via pre-commit | Riusa `.pre-commit-config.yaml`: un'unica fonte di verità tra locale e CI. |
| **test** | `pytest spark_apps/tests` (unit) | Trasformazioni silver su DataFrame in memoria. Esclude `tests/integration/`. |
| **dbt-validate** | `dbt parse` | Valida SQL e `ref()`/`source()` senza connettersi a Trino. |
| **compose-validate** | `docker compose config` + check versioni | Sintassi compose e coerenza Scala/Spark/Delta (4.0.0/2.13). |
| **integration-test** | Postgres + Kafka **veri** (service container) | Vedi sotto. |
| **dag-integrity** | `DagBag` sui DAG Airflow | Import puliti, niente cicli, `owner`/`retries`/`catchup` impostati esplicitamente. |

`lint`, `test`, `dbt-validate`, `compose-validate` girano in parallelo, senza dipendenze fra loro.

## Il job `integration-test` (Postgres + Kafka reali)

I unit test in `spark_apps/tests/` passano DataFrame costruiti a mano:
veloci, ma non avrebbero **mai** intercettato il bug storico di questo
progetto (`debezium_schema` definito ma mai usato → bronze pieno di null),
perché non toccano mai un vero messaggio Kafka con l'envelope Debezium.

Questo job accende due service container veri:

- **Postgres** — `scripts/check_postgres_cdc_readiness.sh` imposta
  `wal_level=logical` (il Postgres ufficiale non lo accetta via env, solo
  via comando, che i service container di Actions non supportano — lo
  script lo scrive in `postgresql.conf` e riavvia il container), applica
  `init-db/init.sql`, poi crea davvero una publication + uno slot di replica
  logica: esattamente quello che fa Debezium alla prima connessione.
- **Kafka** (KRaft, `bitnami/kafka`) — `spark_apps/tests/integration/test_bronze_kafka_integration.py`
  produce un envelope Debezium reale su un topic reale, poi fa leggere il
  messaggio a Spark con la stessa identica trasformazione di `cdc_bronze.py`.

`kafka-python` è usato solo per **produrre** il messaggio di test; la
*lettura* passa da Spark (`spark.read.format("kafka")`), per testare il
codice di produzione così com'è, non una sua reimplementazione.

## Airflow: orchestrazione del layer gold

File: `airflow/Dockerfile`, `docker-compose.airflow.yml` (overlay, non
tocca `docker-compose.yaml`), `dags/`, `requirements-airflow.txt`,
`env.airflow.example`.

Avvio:
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yml up -d
```
UI su `http://localhost:8090` (8080/8081 già occupati da kafka-ui/spark-master).

**Punto architetturale importante.** `cdc_bronze.py` e `cdc_silver.py` sono
job di streaming continuo (`awaitTermination()`): restano vivi come processi
di lungo periodo, non "finiscono" mai. Airflow **non** li lancia — se lo
facesse a ogni run pianificata, ogni esecuzione aprirebbe un nuovo consumer
Kafka concorrente sullo stesso topic invece di riavviare quello esistente.
Restano avviati come oggi, a mano o via `spark_bronze.bash`/`spark_silver.bash`.

Quello che Airflow orchestra è la parte **batch** a valle, in due DAG:

- **`cdc_batch_pipeline`** (`@hourly`): `check_streaming_alive` (interroga la
  REST API dello Spark Master, fallisce fail-fast se bronze/silver non
  risultano attivi) → `dbt_build_gold` (`docker compose run --rm dbt dbt build`)
  → `great_expectations_validate` (`docker compose run --rm great-expectations`).
- **`cdc_maintenance`** (`@weekly`): `delta_vacuum`, via `docker exec spark-master`
  (coerente con `spark_apps/spark_bronze.bash`, che usa lo stesso pattern —
  qui è corretto perché spark-master è già un servizio long-running, a
  differenza di dbt/great-expectations che sono lanciati on-demand).

**Perché `docker exec`/`docker compose run` invece di operator "nativi" tipo
`SparkSubmitOperator`?** Lo scheduler Airflow parla col demone Docker
dell'host tramite il socket montato (`/var/run/docker.sock`), riusando
esattamente i comandi che già si lanciano a mano da terminale — zero nuova
superficie da imparare. Il costo: il container Airflow ha di fatto controllo
root-equivalente sull'host. Accettabile per uno stack locale/portfolio;
in produzione si userebbe un executor remoto (Kubernetes/Celery) o operator
dedicati che parlano con Spark via rete, non via socket montato.

`dags/tests/test_dag_integrity.py` verifica: nessun errore di import, almeno
2 DAG trovati, nessun ciclo, `owner`+`retries` impostati, `catchup=False`
esplicito, tag presenti. Gira nel job `dag-integrity` di `ci.yml`.

## Cosa fa `docker-build.yml`

Builda l'immagine Spark dal `dockerfile`. Sulle **PR** fa solo build; su
**main** builda *e* pusha su `ghcr.io`. Cache dei layer perché il dockerfile
scarica molti jar da Maven.

## Le decisioni di design (il *perché*, in sintesi)

**Perché non `dbt build` in CI?** Richiederebbe Trino + Delta + MinIO accesi.
`dbt parse` intercetta la maggior parte degli errori a costo quasi zero;
l'integrazione vera contro dati reali resta locale (o nel DAG Airflow).

**Perché `requirements-dev.txt`/`requirements-airflow.txt` separati?**
pytest/pre-commit/Airflow non servono in produzione, e Airflow ha un grafo
di dipendenze molto vincolato (constraints ufficiali): mischiarlo con
Spark/dbt creerebbe conflitti di risoluzione.

**Perché il check versioni Scala/Spark/Delta è un job a sé?** Il mismatch dà
errori runtime *silenziosi* (ClassNotFound). Meglio un gate automatico.

## Possibili estensioni

- **CD vero**: deploy automatico su un ambiente al tag di release.
- **Trivy** o scan di sicurezza sull'immagine Docker prima del push.
- Estrarre la logica di parsing di `cdc_bronze.py` in una funzione
  importabile (come `make_process_batch` per la silver), per non duplicare
  lo schema Debezium nel test di integrazione — pianificato in
  [ROADMAP.md](../ROADMAP.md), Fase 1.
