# Roadmap — da demo CDC a pipeline production-ready

Stato di partenza: `59ed7bf` (CI/CD + Airflow). Questo documento è la roadmap
di sviluppo verso gli obiettivi di progetto, con le decisioni di stack già prese
e i criteri di uscita per ogni fase.

---

## Decisioni di stack (bloccate)

| Ambito | Scelta | Perché |
|---|---|---|
| Stream engine | **Solo Spark Structured Streaming** | Nessuna nuova infra: checkpoint, Delta e `foreachBatch` coprono ordering, dedup, late events e idempotenza. Un secondo engine (Flink) raddoppierebbe la superficie da mantenere senza aggiungere obiettivi coperti. |
| Scrittura sui sink | **`foreachBatch` da Spark** | Un solo runtime. Idempotenza esplicita via `batch_id` + guardia su `source_lsn`, che è comunque il concetto da saper spiegare. |
| Schema Registry | **Confluent Schema Registry + Avro** | Confluent Community License: gratuita, self-hosted senza limiti (vietato solo rivenderla come SaaS concorrente). È il registry citato nella maggior parte delle job description. Costo: immagine Debezium custom con `kafka-connect-avro-converter` (i converter Confluent non sono nell'immagine ufficiale, quelli Apicurio sì). |
| Deployment | **docker-compose hardened** | Healthcheck su tutti i servizi, resource limits, secrets fuori dai file, container non-root, test e2e in CI. Un revisore clona e con un comando vede la pipeline girare: vale più di un chart Helm incompleto. |

---

## Modalità di lavoro

Il progetto ha due obiettivi insieme — imparare tecnologie mai usate (Kafka,
Debezium, Trino, dbt, GE) e costruire un portfolio credibile — con colloqui a
1-2 mesi e ~15 ore a settimana disponibili. Da qui la divisione del lavoro.

### Chi scrive cosa

| Tipo di lavoro | Chi | Perché |
|---|---|---|
| Impalcatura: compose, Dockerfile, jar e versioni, JMX exporter, wiring Prometheus | **Claude** | Resa didattica per ora bassissima, frustrazione alta. Esempio di ciò che costa serate senza insegnare niente: `dockerfile` scarica `delta-storage-3.3.0` con `delta-spark-4.0.0` → `ClassNotFoundException` opaco a runtime, e il check di versioni in CI grepPa solo `delta-spark`. |
| Logica semantica: MERGE con guardia LSN, dedup, watermark, sink idempotenti, script di replay | **Pascal** | È letteralmente il contenuto delle risposte da colloquio. Derivare la soluzione ≠ riconoscerla. |
| Rottura deliberata e debug | **Pascal guida**, Claude fa da sistema di suggerimenti | Il meccanismo di apprendimento più forte in questo dominio |
| ADR e documenti (`delivery-semantics.md`, `schema-evolution.md`, runbook) | **Pascal** | Scrivere è dove scopri di non aver capito. E questi documenti *sono* le risposte da colloquio. |
| Modelli dbt | **Pascal** | Il più facile dei tool nuovi: si impara facendo, review veloce |

**Regola trasversale: chiunque scriva, l'altro predice prima.** Prima di leggere
un'implementazione di Claude, Pascal scrive cosa si aspetta di trovare. Prima di
una review, scrive quale parte ritiene fragile. La distanza tra predizione ed
esito è ciò che si sta imparando.

### Loop per ogni fase

1. **Claude: spike minimo funzionante** (~20% del tempo) — la config che altrimenti costa quattro ore di ricerca
2. **Pascal: rompilo** (~30%) — osservare il failure mode con i propri occhi (Kafka UI, `pg_replication_slots`, la riga null in Bronze)
3. **Pascal: scrive il fix** (~30%) — review di Claude a effort alto
4. **Pascal: scrive l'ADR** (~20%) — 15 righe: qual era il failure, perché la fix funziona, quale trade-off è stato accettato. Poi Claude interroga come farebbe un intervistatore.

### Policy di review

Tutti e quattro gli assi richiesti, ma sequenziati — la review di performance
prima che la correttezza sia chiusa produce solo rumore:

| Asse | Quando |
|---|---|
| Correttezza sotto failure (out-of-order, replay, duplicati, crash a metà batch) | **Ogni** consegna, senza sconti |
| Domande da intervistatore | Fine di ogni fase, sull'ADR scritto |
| Qualità e idiomaticità | Inline durante la review, priorità bassa |
| Performance (skew, small files, broadcast join, dimensionamento micro-batch) | Fase 7 su numeri misurati — **tranne** le scelte strutturalmente difficili da disfare (partizionamento, layout dei file), segnalate subito |

---

## Ordine di esecuzione e budget

Ordine rivisto per l'orizzonte colloqui: le fasi 4 e 5 (delivery semantics e
reprocessing) sono quelle su cui si viene davvero interrogati, quindi passano
davanti a schema registry e sink extra. Le fasi 0-1-2 restano prerequisiti
tecnici non aggirabili: senza `source_lsn` in Bronze e senza una MERGE corretta,
4 e 5 non sono implementabili.

| Ordine | Fase | Ore stimate | Cumulato |
|---|---|---|---|
| 1 | **-1** Kafka bootcamp | 3 | 3 |
| 2 | **0.5** Flusso git production-ready | 4 | 7 |
| 3 | **0** Coerenza e correttezza | 10 | 17 |
| 4 | **1** Bronze event store | 12 | 29 |
| 5 | **2** Silver corretto | 18 | 47 |
| 6 | **4** Delivery semantics | 14 | 61 |
| 7 | **5** Reprocessing & backfill | 16 | 77 |
| 8 | **3** Schema evolution | 12 | 89 |
| 9 | **6** Output sinks | 8 | 97 |
| 10 | **7** Observability & prod-readiness | 14 | 111 |

A 15 ore a settimana: **~5 settimane per avere tutto il materiale
interview-critical** (fino alla fase 5), ~7-8 per la roadmap completa.

La fase 0.5 va prima della 0 di proposito: le fasi successive produrranno un
centinaio di commit, e devono passare tutte dal flusso corretto. Impostarlo dopo
significherebbe avere la parte più interessante del progetto sviluppata in push
diretti su `main`.

Perché la fase 3 (Avro + registry) può stare in fondo senza costare rework: il
refactor della fase 1 isola il parsing in `build_bronze_df(raw_df)`, e Silver e i
sink consumano la tabella Delta, non i byte Kafka. Cambiare serializzazione tocca
quindi una funzione sola. È anche il motivo per cui quel confine di astrazione va
creato in fase 1 e non dopo.

## Mappa obiettivi → fasi

| Obiettivo | Stato iniziale | Fasi che lo chiudono |
|---|---|---|
| 1. CDC Ingestion | 🟡 40% | 0, 1 |
| 2. Stream Processing Logic | 🟡 35% | 2 |
| 3. Schema Evolution | 🔴 0% | 3 |
| 7. Delivery Semantics | 🔴 10% | 4 |
| 8. Reprocessing & Backfills | 🔴 5% | 5 |
| 9. Output Sinks | 🔴 20% | 6 |
| Production readiness | 🟡 | 7 |

---

## Fase -1 — Kafka bootcamp (3 ore, prima di toccare il codice)

Baseline dichiarata: concetti Kafka confusi. Le fasi 2, 4 e 5 poggiano interamente
su offset, consumer group, chiavi/partizioni e compaction: affrontarle senza quei
concetti significa eseguire istruzioni, non imparare.

Lab guidato: [docs/learning/01-kafka-fundamentals.md](docs/learning/01-kafka-fundamentals.md)
— gira sul cluster Kafka del compose, sei sezioni con predizione obbligatoria
prima di ogni comando, e otto domande di autovalutazione che sono domande da
colloquio. Ogni concetto è collegato al punto della pipeline dove serve (incluso
il bug dei tombstone in Bronze, che il lab fa vedere dall'origine).

**Criterio di uscita:** le 8 domande finali risposte a voce senza rileggere.

---

## Fase 0.5 — Flusso git production-ready (4 ore)

Dettaglio completo, con stato attuale verificato e razionale:
[docs/git-workflow.md](docs/git-workflow.md).

Oggi la CI gira ma **non protegge niente**: `gh api .../branches/main/protection`
risponde `404 Branch not protected` e nella storia del repo non esiste **nessuna
PR**. Un push con i test rossi entra su `main` senza attriti. "Ho una CI con sei
job" e "ho una CI con sei job obbligatori prima del merge" sono affermazioni molto
diverse, e la seconda è verificabile da chiunque apra il repo — che è pubblico.

Tre cose da correggere prima di eseguire lo script che hai già scritto:

1. `scripts/setup-branch-protection.sh` imposta `required_approving_review_count=1`
   con `enforce_admins=true`. GitHub **non permette di approvare la propria PR**:
   così com'è, quello script rende il merge impossibile su un repo a maintainer
   singolo. Va portato a 0, con i required status check a garantire la qualità.
2. Il repo è **pubblico e senza LICENSE**, mentre il README dichiara MIT: GitHub
   non mostra licenza, quindi formalmente il codice è "tutti i diritti riservati".
3. Nessun gate sui secret, e in history c'è un `MINIO_SECRET` hardcoded (valore
   `minioadmin`, quindi innocuo — ma il controllo che avrebbe fermato uno vero
   non c'è).

Quattro blocchi: `main` protetta e flusso PR (1h) · igiene della history —
branch stale ✅ *fatto 26/08*, identità autore ✅ *fatto 26/08*, cleanup file
di runtime in history ✅ *fatto 26/08* (740 blob / 562 MB sotto `data/`,
`.git` 6 MB → 440 KB), LICENSE, `.gitattributes` (restano ~0.5h) · gate
automatici — gitleaks, commitlint, hadolint, shellcheck, sqlfluff,
dependabot, least-privilege sui workflow (1.5h) · versionamento e release
con tag semver per fase (0.5h).

**Criterio di uscita:** la prima PR del progetto (quella della fase 0) mergiata
con sei check verdi obbligatori e branch cancellato in automatico.

---

## Fase 0 — Coerenza e correttezza (2-3 giorni)

Oggi la pipeline, come è committata, **non cattura nulla**: il backend scrive sul
database `ecommerce`, il connector Debezium osserva `inventory.public.orders`, e il
compose non monta `init-db/` (quindi `ecommerce` non viene mai creato). Prima di
aggiungere feature, la catena deve funzionare end-to-end.

### 0.1 Un solo database di verità

- `ecommerce` come DB unico; `init-db/` montato su `/docker-entrypoint-initdb.d`
- backend nel `docker-compose.yaml` con profilo `docker` (porta 8085 → allineata a `prometheus.yml`)
- connector Debezium puntato su `ecommerce`

### 0.2 Connector Debezium hardened + config-as-code

`debezium/connectors/orders.json` versionato, registrato via `PUT /connectors/<name>/config`
(idempotente, a differenza dell'attuale `POST` che fallisce alla seconda esecuzione):

- `slot.name` / `publication.name` espliciti, `publication.autocreate.mode: filtered`
- `snapshot.mode: initial` dichiarato (snapshot vs streaming diventa una scelta documentata, non un default implicito)
- **`heartbeat.interval.ms`** — senza heartbeat, con DB idle il replication slot trattiene WAL fino a riempire il disco: l'incidente CDC più comune in produzione
- `decimal.handling.mode: double`, `time.precision.mode` dichiarato
- `tombstones.on.delete` scelto esplicitamente

### 0.3 Bug da correggere

| # | File | Problema |
|---|---|---|
| 1 | `spark_apps/cdc_bronze.py:51` | `total_amount` è `DECIMAL(19,4)`: con `decimal.handling.mode` default (`precise`) Debezium lo serializza come bytes base64 → letto come `DoubleType` dà `null` |
| 2 | `spark_apps/cdc_bronze.py:53` | `created_at`/`updated_at` sono `TIMESTAMPTZ` → Debezium emette stringa ISO-8601, lo schema dichiara `LongType` (→ `null`), e `gold_orders_daily.sql` assume microsecondi. Tre convenzioni incompatibili |
| 3 | `spark_apps/cdc_bronze.py:89` | Tombstone non gestiti: `value=null` → `from_json` appende in Bronze una riga interamente `null` |
| 4 | `spark_apps/cdc_silver.py:57` | `whenMatchedUpdateAll()` senza guardia di ordinamento: un update vecchio sovrascrive uno nuovo (sistematico durante i replay) |
| 5 | `spark_apps/cdc_silver.py:65` | Delete in una seconda MERGE dopo gli upsert → la sequenza `d`→`c` nello stesso batch viene invertita |
| 6 | `spark_apps/cdc_silver.py:94` | `user_df`/`item_df` letti da JDBC una volta all'avvio e cachati: enrichment permanentemente stale |
| 7 | `common/outbox/OutboxService.java:31` | `outboxRepository.save(newEvent)` chiamato due volte |
| 8 | `great_expectations/expectations/silver_orders_suite.json:20` | Attende `status` minuscolo, l'enum `OrderStatus` è maiuscolo → expectation sempre fallita |
| 9 | `great_expectations/validate.py:60` | Su fallimento fa solo `logger.warning` ed esce con 0 → nessun quality gate: il task Airflow non fallisce mai |
| 10 | `README.md` | Dichiara dashboard Grafana su consumer lag e batch duration; `prometheus.yml` scrapa solo l'actuator del backend e in git non esiste alcuna dashboard |

**Criterio di uscita:** `docker compose up` + `POST /api/orders` → riga in Bronze con
importi e timestamp non-null, verificata da un test e2e in CI.

---

## Fase 1 — Bronze come vero event store (3-4 giorni) → obiettivi 1, 7, 8

Bronze oggi butta via tutto ciò che serve a valle: nessun metadato Kafka
(`key`, `partition`, `offset`, `timestamp`), nessun campo `source` di Debezium
(`lsn`, `txId`, `ts_ms`, `snapshot`). Senza questi, ordering (obiettivo 2),
idempotenza (7) e replay-from-timestamp (8) sono impossibili per costruzione.

- envelope completo: `before`/`after` come struct, `op`, `source.*`, metadati Kafka, payload raw come colonna di fallback
- refactor in `build_bronze_df(raw_df)` puro e testabile — elimina la duplicazione dello schema in `tests/integration/test_bronze_kafka_integration.py`, che oggi può disallinearsi in silenzio
- CDC estesa a `users`, `order_items` e `outbox_events` (con EventRouter SMT: chiude il pattern outbox lasciato a metà nel backend)
- un test per ciascun caso: `op=r` (snapshot), `c`, `u`, `d`, tombstone

**Criterio di uscita:** da Bronze si può ricostruire lo stato di `orders` a un
timestamp arbitrario usando solo i suoi campi.

---

## Fase 2 — Silver corretto (1 settimana) → obiettivo 2

- dedup per chiave nel micro-batch: `row_number() over (partition by id order by source_lsn desc)`
- **MERGE unica** con guardia `s.source_lsn < b.source_lsn` per upsert e delete → ordering garantito e MERGE idempotente sotto replay
- soft delete (`is_deleted`, `deleted_at`) invece di hard delete: audit preservato
- enrichment via dimension table Delta alimentata da CDC (stream-static join), al posto del JDBC cachato
- watermark su event time + tabella/metrica `late_events`
- `docs/adr/002-partitioning-keys.md`: Debezium chiava per PK → ordine garantito per-key dentro la partizione; cosa si rompe cambiando il numero di partizioni

**Criterio di uscita:** un test che riproduce eventi fuori ordine e verifica che
Silver converga allo stato corretto indipendentemente dall'ordine di arrivo.

---

## Fase 3 — Schema Registry & evolution (1 settimana) → obiettivo 3

- Confluent Schema Registry nel compose + immagine Debezium custom con `kafka-connect-avro-converter`
- compatibilità `BACKWARD` forzata a livello di subject
- scenari dimostrati via migrazioni Flyway, con esito documentato per ognuno:
  - `V5` colonna nullable aggiunta
  - `V6` enum expansion su `OrderStatus`
  - `V7` colonna rimossa
- job CI `schema-compat`: blocca la PR se una migrazione rompe la compatibilità
- `mergeSchema` Delta controllato da allowlist, non aperto

**Criterio di uscita:** `docs/schema-evolution.md` con i tre scenari, cosa è
successo a monte e a valle, e quale ha richiesto intervento manuale.

---

## Fase 4 — Delivery semantics (4-5 giorni) → obiettivo 7

- Redis sink idempotente: last-write-wins per `source_lsn` (script Lua / compare-and-set)
- Postgres audit append-only: `ON CONFLICT (event_id) DO NOTHING` + tabella `processed_batches(batch_id)`
- DLQ topic per messaggi non parsabili, con retry e backoff
- producer idempotente/transazionale sui topic derivati
- **deliverable principale:** `docs/delivery-semantics.md` — la catena anello per anello
  (Debezium → Kafka → Spark → sink), dove esattamente si perde l'exactly-once e perché,
  con i trade-off latenza/garanzie espliciti

---

## Fase 5 — Reprocessing & backfill (1 settimana) → obiettivo 8

Il differenziatore. Tre scenari eseguibili, ognuno con script + runbook:

| Scenario | Strategia |
|---|---|
| Regola cambiata | Rebuild Silver da Bronze via Delta time travel in shadow table + swap atomico, senza toccare Kafka |
| Bug fixato | Replay da timestamp: `kafka-consumer-groups --reset-offsets --to-datetime` |
| Nuovo sink aggiunto | Debezium **incremental snapshot** via signal table, senza fermare lo stream |

- DAG Airflow `cdc_backfill` parametrizzato (`from_ts`, `to_ts`, `target`, `dry_run`)
- test di idempotenza: esegue il replay due volte e verifica che Silver sia identico

---

## Fase 6 — Output sinks (3-4 giorni) → obiettivo 9

- Redis read model: `order:{id}`, `customer:{email}:summary`, TTL dichiarati
- Postgres history/audit con `valid_from`/`valid_to`
- opzionali successivi: Elasticsearch, export Parquet partizionato

---

## Fase 7 — Observability e production readiness (1 settimana)

- kafka-exporter (consumer lag), JMX exporter su Kafka e Debezium
- `StreamingQueryListener` Spark → metriche custom: batch duration, rows/s, late events, DLQ depth
- **lag del replication slot** (`pg_replication_slots.confirmed_flush_lsn`): l'allarme che conta davvero
- dashboard Grafana e datasource come codice, in git
- alert rules: consumer lag, slot lag, streaming query down, DLQ non vuota, GE failure
- quality gate reale: GE fallisce → task Airflow fallisce → gold non si aggiorna
- hardening: secrets fuori da `.env`, container non-root, resource limits, healthcheck su tutti i servizi, retention/compaction Kafka documentate
- chiusura: `docs/adr/`, runbook di incident (slot bloat, DLQ non vuota, breaking schema change), e **latenza end-to-end misurata p50/p99**

---

## Learning log

`docs/learning-log.md`: una voce per sessione, dieci righe — cosa non funzionava,
cosa è stato provato, perché la soluzione funziona. In colloquio quelle voci
diventano storie concrete, che valgono dieci volte una definizione corretta.

---

## Bonus ad alto ritorno

**Propagazione GDPR del delete** (right-to-be-forgotten attraverso Bronze immutabile,
Silver e Redis): usa tombstone, soft delete e Delta DELETE insieme, e dimostra
comprensione del problema, non solo dell'API.
