# ADR 002 — Configurazione della guardia MERGE upsert su Silver (`cdc_silver.py`)

## Failure

`whenMatchedUpdateAll()` applicava ogni update nell'ordine di *ingestion*
(l'ordine in cui il micro-batch arrivava a Spark), non nell'ordine
*cronologico* reale dell'evento. Un update stale, arrivato dopo uno più
recente (tipicamente per via di un replay), sovrascriveva senza controlli
lo stato più aggiornato già presente in Silver.

La causa a monte: Bronze oggi non porta `source_lsn` (arriva in Fase 1,
"Bronze come vero event store") — l'unico ordine disponibile è quello di
arrivo del batch, non quello del WAL sorgente.

## Come funziona la guardia

Guardia su `whenMatchedUpdateAll(condizione)`, tre rami in OR, valutati
nell'ordine seguente:

1. **`updated_at` più fresco** — `s.updated_at < b.updated_at AND b.updated_at IS NOT NULL`:
   se il timestamp applicativo in arrivo è strettamente più recente di
   quello già in Silver, l'update passa.
2. **Fallback su `version`** — scatta quando `updated_at` è in pareggio tra le due righe,
   o quando quello in arrivo è `NULL`: in entrambi i casi `updated_at` da solo non
   basta a decidere, quindi si richiede che `version` sia più alta di quella
   già presente in Silver.
3. **Riga esistente senza `updated_at`** — `s.updated_at IS NULL AND b.updated_at IS NOT NULL`:
   se in Silver c'è un `updated_at` nullo (es. scritto da un ramo precedente
   che non aveva il campo) e l'update in arrivo ce l'ha, l'update passa
   sempre — non c'è un timestamp target con cui confrontare.

Verificato con test mirati, uno scenario per ramo (bug #4,
`test_bug4_update_vecchio_sovrascrive_stato_piu_recente` in
`spark_apps/tests/test_silver_bugs.py`).

## Trade-off accettato

`updated_at` e `version` sono campi applicativi, non garanzie del database.
Si perde la garanzia d'ordine che Debezium legge direttamente dal WAL —
l'ordine reale con cui Postgres ha scritto i dati. La guardia si affida
invece a due proxy:

- **`version`** dipende dalla disciplina con cui l'applicazione lo
  incrementa ad ogni scrittura. Un bug che se lo dimentica anche una sola
  volta rompe la guardia silenziosamente, senza errori visibili.
- **Collisione sotto concorrenza, anche con l'app corretta**: due
  transazioni che leggono lo stesso `version` di partenza possono
  generare lo stesso valore pur avendo un ordine WAL reale diverso (una
  committa prima dell'altra). La guardia non può distinguerle — l'update
  "vero" più recente viene scartato perché `s.version < b.version` non è
  più strettamente vero. Un LSN, per come Postgres lo genera, non può
  collidere per costruzione: qui è un **limite strutturale del
  meccanismo**, non un bug risolvibile con più disciplina applicativa.

**Fase 1**: quando `source_lsn` sarà disponibile in Bronze, sostituisce
interamente `updated_at`/`version` — non resta come fallback. La guardia
diventa `s.source_lsn < b.source_lsn AND b.source_lsn IS NOT NULL`.
