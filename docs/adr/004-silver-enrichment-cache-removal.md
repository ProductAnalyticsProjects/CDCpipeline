# ADR 004 — Rimozione della cache su `user_df`/`item_df` in Silver (`cdc_silver.py`)

## Failure

`user_df` veniva letto da Postgres via JDBC una volta sola, all'avvio dello
stream, e cachato con `.cache()`. Un utente registrato dopo quel momento
non esisteva in quello snapshot: un ordine di quell'utente, arrivato in un
qualsiasi batch successivo, non trovava match nel `left join` di
`enrich_orders` — anche se nella tabella Postgres reale l'utente era già
presente da tempo. Non un ritardo temporaneo: lo snapshot non scade mai,
quindi l'enrichment restava `null` per sempre, per tutta la vita dello
stream.

## Come funziona la fix

Rimosso `.cache()` da `user_df`. Spark è lazy: un DataFrame costruito da
una sorgente esterna (JDBC, o un path Delta/file) non esegue la query al
momento della costruzione, la esegue ogni volta che un'azione a valle lo
tocca. Senza `.cache()` a materializzarlo una volta per tutte, ogni batch
che passa da `enrich_orders` rilancia la lettura e vede lo stato *attuale*
della tabella sorgente.

Un punto verificato con un test dedicato, non ovvio: questo funziona solo
perché la sorgente è una lettura fisica esterna (JDBC in produzione, un
path Delta nel test). Un tentativo di simulare lo stesso comportamento con
una vista temporanea Spark SQL (`createOrReplaceTempView`) **non
funziona** — Spark risolve il nome della vista contro il catalogo nel
momento in cui il DataFrame viene costruito, non ad ogni esecuzione
successiva; sovrascrivere la vista dopo non cambia un DataFrame già
costruito. Una lettura da path (Delta, o JDBC) invece riesegue davvero la
scansione ad ogni chiamata, perché è una lettura da una sorgente esterna
allo stato di Spark, non un riferimento interno al catalogo.

## Trade-off accettato

Questa architettura non scala: un round-trip JDBC completo ad ogni
micro-batch, invece di uno solo all'avvio. Accettato deliberatamente come
fix a effort minimo — la performance è esplicitamente rimandata a Fase 7
in ROADMAP.md, misurata su numeri reali. La soluzione strutturale (una
dimension table Delta alimentata da CDC, stream-static join invece del
JDBC ripetuto) è pianificata in Fase 2, insieme al resto del refactor di
Silver: rifarla ora, prima di quel refactor, sarebbe lavoro da rifare due
volte.
