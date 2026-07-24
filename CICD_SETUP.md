# CI/CD per CDCpipeline — setup e razionale

Pipeline GitHub Actions per il progetto CDC, pensata per dare feedback veloce
senza dover accendere l'intero stack, più orchestrazione Airflow del layer
gold e branch protection su `main`.

## Come installarli

Questi file sono organizzati esattamente come nella root del repo
`CDCpipeline` (`.github/`, `dags/`, `airflow/`, `scripts/`,
`spark_apps/tests/integration/`, ecc.). Per installarli: copia questa intera
cartella sopra la tua copia locale del repo (sovrascrivendo solo le
sottocartelle nuove — non tocca `dbt_project/`, `spark_apps/cdc_bronze.py` e
gli altri file esistenti, perché non esistono qui), poi committa:

```bash
# dalla root del tuo clone locale di CDCpipeline
rsync -a --exclude 'cv_pascal_bigdata*.docx' --exclude 'CICD_SETUP.md' \
  "/percorso/a/CDC per per senior data engineer/" .
chmod +x scripts/*.sh

git add .github dags airflow spark_apps/tests/integration requirements-dev.txt \
        requirements-airflow.txt docker-compose.airflow.yml env.airflow.example scripts
git commit -m "ci: add GitHub Actions pipeline, Airflow orchestration, branch protection"
git push
```

(`cv_pascal_bigdata*.docx` sono i tuoi CV, non fanno parte della pipeline —
escludili dalla copia. `CICD_SETUP.md` è questo stesso file: tienilo qui come
riferimento o spostalo in `docs/` nel repo, come preferisci.)

Aggiungi anche le variabili di `env.airflow.example` al tuo `.env` (vedi
sezione Airflow più sotto) prima di avviare l'overlay.

Da quel momento ogni push e ogni PR fanno partire i controlli. Li vedi nel
tab **Actions** del repo e come check ✅/❌ dentro le PR.

## Cosa fa `ci.yml` (6 job)

| Job | Cosa verifica | Perché così |
|-----|---------------|-------------|
| **lint** | ruff + ruff-format via pre-commit | Riusa il tuo `.pre-commit-config.yaml`: un'unica fonte di verità. |
| **test** | `pytest spark_apps/tests` (unit) | Trasformazioni silver su DataFrame in memoria. Esclude `tests/integration/`. |
| **dbt-validate** | `dbt parse` | Valida SQL e `ref()`/`source()` senza connettersi a Trino. |
| **compose-validate** | `docker compose config` + check versioni | Sintassi compose e coerenza Scala/Spark/Delta (4.0.0/2.13). |
| **integration-test** | Postgres + Kafka **veri** (service container) | Vedi sotto — questo è il job che avrebbe intercettato il bug storico del progetto. |
| **dag-integrity** | `DagBag` sui DAG Airflow | Import puliti, niente cicli, `owner`/`retries`/`catchup` impostati esplicitamente. |

`lint`, `test`, `dbt-validate`, `compose-validate` girano in parallelo, senza dipendenze fra loro.

## Il job `integration-test` (Postgres + Kafka reali)

I unit test esistenti (`spark_apps/tests/`) passano DataFrame costruiti a
mano: veloci, ma non avrebbero **mai** intercettato il bug storico di questo
progetto (`debezium_schema` definito ma mai usato → bronze pieno di null),
perché non toccano mai un vero messaggio Kafka con l'envelope Debezium.

Questo job accende due service container veri:

- **Postgres** — `scripts/check_postgres_cdc_readiness.sh` imposta
  `wal_level=logical` (il Postgres ufficiale non lo accetta via env, solo
  via comando, che i service container di Actions non supportano — lo
  script lo scrive in `postgresql.conf` e riavvia il container), applica
  `init-db/init.sql`, poi crea davvero una publication + uno slot di replica
  logica: esattamente quello che fa Debezium alla prima connessione. Se
  `wal_level` non fosse logical, questo fallirebbe con un errore chiaro
  invece di scoprirlo a runtime nel connettore.
- **Kafka** (KRaft, `bitnami/kafka`) — `spark_apps/tests/integration/test_bronze_kafka_integration.py`
  produce un envelope Debezium reale su un topic reale, poi fa leggere il
  messaggio a Spark con la stessa identica trasformazione di `cdc_bronze.py`
  (schema duplicato nel test — vedi nota nel file sul perché e su come
  evitarlo in futuro estraendo una funzione condivisa).

`kafka-python` è usato solo per **produrre** il messaggio di test; la
*lettura* passa da Spark (`spark.read.format("kafka")`), per testare il
codice di produzione così com'è, non una sua reimplementazione.

## Airflow: orchestrazione del layer gold

File aggiunti: `airflow/Dockerfile`, `docker-compose.airflow.yml` (overlay,
non tocca il tuo `docker-compose.yaml`), `dags/`, `requirements-airflow.txt`,
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
esattamente i comandi che già lanci a mano da terminale — zero nuova
superficie da imparare. Il costo: il container Airflow ha di fatto controllo
root-equivalente sull'host. Accettabile per uno stack locale/portfolio;
in produzione useresti un executor remoto (Kubernetes/Celery) o operator
dedicati che parlano con Spark via rete, non via socket montato. Vale la
pena saperlo spiegare in un colloquio, non solo saperlo far girare.

`dags/tests/test_dag_integrity.py` verifica: nessun errore di import, almeno
2 DAG trovati, nessun ciclo, `owner`+`retries` impostati, `catchup=False`
esplicito, tag presenti. Gira nel job `dag-integrity` di `ci.yml`.

## Cosa fa `docker-build.yml`

Builda l'immagine Spark dal `dockerfile`. Sulle **PR** fa solo build; su
**main** builda *e* pusha su `ghcr.io`. Cache dei layer perché il dockerfile
scarica molti jar da Maven.

## Branch protection

`scripts/setup-branch-protection.sh` (richiede `gh auth login` + permessi
admin sul repo) configura su `main`:

- i 6 check di `ci.yml` obbligatori e verdi prima del merge
- 1 review approvata richiesta, scartata automaticamente a nuovi commit
- niente force-push, niente cancellazione del branch
- regola valida anche per te come admin (`enforce_admins=true`)

**Deliberatamente escluso**: il job `docker` di `docker-build.yml`. Ha un
filtro `paths:` (gira solo se cambiano dockerfile/requirements/spark_apps):
un required check che su alcune PR non viene mai creato blocca il merge per
sempre — un errore comune da evitare.

```bash
bash scripts/setup-branch-protection.sh ProductAnalyticsProjects/CDCpipeline main
```

Serve che i workflow abbiano già girato almeno una volta su `main` prima di
lanciarlo (GitHub registra un check come "richiedibile" solo dopo la prima
esecuzione). In alternativa, stessa configurazione a mano da
**Settings → Branches → Add branch protection rule**.

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
- **Trivy / scan di sicurezza** sull'immagine Docker prima del push.
- Estrarre la logica di parsing di `cdc_bronze.py` in una funzione
  importabile (come `make_process_batch` per la silver), per non duplicare
  lo schema Debezium nel test di integrazione.

## Limiti di questa verifica

Il sandbox in cui ho preparato questi file non ha Docker, quindi non ho
potuto eseguire per intero `docker compose up` con l'overlay Airflow né il
job `integration-test` con i service container reali (Postgres/Kafka).
Ho verificato concretamente: sintassi YAML di tutti i workflow, `ruff check`
e `dbt parse` contro il repo reale, sintassi Python/bash di DAG/test/script,
e — installando davvero `apache-airflow==2.9.3` — `pytest dags/tests`:
**7/7 test passati** contro i DAG reali (`DagBag` li importa senza errori,
nessun ciclo, `owner`/`retries`/`catchup`/`tags` tutti presenti). Non
verificato end-to-end: il job `integration-test` (richiede Docker) e
l'overlay `docker-compose.airflow.yml`. La prima esecuzione su GitHub
Actions resta il riscontro finale per quei due — è normale dover aggiustare
qualche dettaglio (timing degli healthcheck, versione immagine bitnami) al
primo run reale.
