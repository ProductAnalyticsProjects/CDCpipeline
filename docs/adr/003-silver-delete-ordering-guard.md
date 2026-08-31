# ADR 003 — Guardia di ordinamento sulla delete in Silver (`cdc_silver.py`)

## Failure

La delete girava in una MERGE separata, dopo quella di upsert, senza
nessuna guardia: `whenMatchedDelete()` cancellava la riga corrispondente
a prescindere da `updated_at`/`version`. Una delete con lo stesso id ma
più vecchia dello stato già presente in Silver (un replay, o un evento
arrivato fuori ordine) cancellava comunque il dato — anche quando quel
dato era più recente della delete stessa.

## Come funziona la fix

La delete guadagna la stessa guardia dell'upsert (bug #4,
`s.updated_at < b.updated_at`, con fallback su `version` — vedi
[ADR 002](002-silver-merge-ordering-guard.md)): cancella solo se l'evento
in arrivo è davvero più recente della riga già presente in Silver.

Il punto meno ovvio è perché l'**ordine** delle due MERGE conti ancora,
anche con la guardia su entrambe. La MERGE di upsert gira per prima; la
MERGE di delete gira dopo, e valuta la sua guardia contro lo stato di
Silver **già aggiornato** dalla prima MERGE — non contro uno snapshot
preso prima dell'inizio del batch. Questo copre due casi distinti,
entrambi verificati con test mirati (`spark_apps/tests/test_silver_bugs.py`):

- **Replay tra batch diversi**: una delete stale che arriva in un batch
  successivo a quando l'ordine è stato ricreato non lo cancella più
  (`test_bug5_delete_vecchia_non_cancella_stato_ricreato_dopo`).
- **Una coppia `d`+`c`/`u` per lo stesso id nello stesso batch**: converge
  correttamente sull'evento più recente dei due, indipendentemente da
  quale sia scritto per primo nel `batch_df`
  (`test_bug5_ultimo_stato_in_silver`). Invertire l'ordine (delete prima
  dell'upsert) rompe questo secondo caso: se la delete gira per prima e
  trova un match, cancella la riga — e il successivo
  `whenNotMatchedInsertAll()` la reinserisce **senza alcuna guardia**,
  perché una riga non più esistente non è mai "matched".

## Trade-off accettato

Questa fix copre solo il caso di **al più un evento upsert e al più un
evento delete** per lo stesso id nello stesso batch. Con **tre o più
eventi** (es. `c`+`u`+`d`, o due `u` e una `d`) per lo stesso id, Delta
fallisce a runtime — "multiple source rows matched" — non produce un
risultato silenziosamente sbagliato, ma un crash del batch.

Risolverlo richiede un dedup per chiave **prima** della MERGE (tenere solo
l'evento più recente per id, via `row_number() over (partition by id
order by version desc)` o equivalente) — lavoro esplicitamente rimandato
a Fase 2, insieme al refactor verso una MERGE unica e al passaggio a soft
delete (che cambierà comunque la forma di questa MERGE, rendendo prematuro
risolvere la deduplicazione ora).
