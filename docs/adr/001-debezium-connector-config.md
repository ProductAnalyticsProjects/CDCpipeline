# ADR 001 — Configurazione del connector Debezium (`debezium/connectors/orders.json`)

Il file di config è scritto per essere corretto e produttivo di default,
ma le scelte dietro ogni riga sono il contenuto vero da saper spiegare in
colloquio. Questo documento è quel contenuto.

## `snapshot.mode: initial`

Alla prima connessione, Debezium fa uno **snapshot** completo della tabella
(legge tutte le righe esistenti come se fossero insert, `op: "r"`) e poi
passa a leggere il WAL in streaming da quel punto in poi. `initial` lo fa
solo se non esiste già uno stato salvato per lo slot — sui riavvii successivi
riparte dal WAL, non rifà lo snapshot. È la scelta giusta quando la tabella
sorgente ha già dati al momento in cui accendi la CDC (il caso normale);
l'alternativa `no_data`/`never` avrebbe senso solo se ti interessano esclusivamente
le modifiche future, ignorando lo stato attuale.

## `slot.name` e `publication.name` espliciti

Senza nominarli, Debezium genera nomi di default legati al nome del
connector. Nominarli esplicitamente serve quando avrai più connector sullo
stesso Postgres (Fase 1: `users`, `order_items`, `outbox_events`) — senza
nomi distinti rischi collisioni o un solo slot condiviso che accoppia
connector che dovrebbero essere indipendenti.

## `publication.autocreate.mode: filtered`

La *publication* è il meccanismo nativo di Postgres (logical replication)
che dice quali tabelle replicare; Debezium ne ha bisogno per usare
`pgoutput`. `filtered` la crea automaticamente includendo solo le tabelle
di `table.include.list` — l'alternativa `all_tables` pubblicherebbe ogni
tabella del database, il che sui privilegi di replica ha un costo e sulla
CDC nessun beneficio se ti servono solo `orders`.

## `heartbeat.interval.ms: 10000`

**Il più importante di questa lista.** Senza heartbeat, se la tabella
sorgente resta inattiva per un periodo prolungato, il replication slot non
avanza mai il suo `confirmed_flush_lsn` — e Postgres non può riciclare i
segmenti WAL più vecchi di quel punto, perché "potrebbero ancora servire al
consumer collegato allo slot". Il WAL cresce senza limite finché il disco
non si riempie. È l'incidente da manuale per chi opera CDC in produzione, e
qui lo previene un solo parametro: l'heartbeat manda un messaggio periodico
anche senza modifiche reali, che fa avanzare comunque il flush del WAL.

Da monitorare in Fase 7: `SELECT slot_name, confirmed_flush_lsn,
pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) AS lag_bytes FROM
pg_replication_slots;` — quel `lag_bytes` che cresce senza fermarsi è
l'allarme che conta più di ogni altro in un sistema CDC.

## `decimal.handling.mode: precise` — e perché NON `double`

Postgres `DECIMAL(19,4)` è un tipo a precisione arbitraria; `double` in
Kafka/Spark è floating-point IEEE 754, che **non può rappresentare
esattamente** molti valori decimali (0.1 in binario è periodico). Per un
importo monetario, la scelta più semplice (`decimal.handling.mode: double`)
introdurrebbe errori di arrotondamento invisibili ma reali — esattamente il
tipo di bug che passa i test e fallisce in produzione su grandi volumi.

`precise` mantiene il valore esatto, ma cambia la rappresentazione sul wire:
il numero arriva come **bytes codificati** (`{"scale": 4, "value":
"<base64>"}` nello schema Debezium), non come numero JSON diretto. Leggerlo
con uno schema Spark `DoubleType` — come fa oggi `cdc_bronze.py` — produce
`null`, perché quei bytes non sono un double. **Questo è il bug #1 della
Fase 0**: la fix corretta non è aggirare il problema tornando a `double` a
livello di connector, ma decodificare correttamente il valore precise-encoded
in Spark. È lavoro deliberatamente lasciato alla logica applicativa, non
alla configurazione — capire questa codifica è esattamente il tipo di
conoscenza CDC che vale in un colloquio.

## `time.precision.mode: adaptive_time_microseconds`

Dichiarato esplicitamente per non dipendere dal default della versione
installata (già cambiato una volta tra major di Debezium). Per una colonna
`TIMESTAMPTZ` come `created_at`/`updated_at`, Debezium emette comunque una
stringa ISO-8601 con offset — questo parametro incide soprattutto su
`TIME`/`TIMESTAMP WITHOUT TIME ZONE`, non elimina il **bug #2**: lo schema
di `cdc_bronze.py` dichiara quelle colonne `LongType` aspettandosi epoch
numerico, quando invece arriva una stringa. Anche questo resta un fix Spark,
non di connector.

## `tombstones.on.delete: true` (il default, dichiarato esplicitamente)

Per ogni delete, Debezium emette **due** messaggi: l'evento con `op: "d"`,
poi un *tombstone* — un messaggio con la stessa chiave e valore `null`. Serve
alla compaction di Kafka per sapere che quella chiave può essere dimenticata
definitivamente (vedi `docs/learning/01-kafka-fundamentals.md`, sezione 5).

`cdc_bronze.py` oggi non lo sa: fa `from_json` sul valore senza controllare
se è null, quindi ogni tombstone diventa una riga interamente null appesa in
Bronze. **Bug #3**: la fix è filtrare (o gestire esplicitamente) i messaggi
a valore null prima del parsing — di nuovo, logica applicativa, non
configurazione del connector.

## Cosa NON è ancora coperto da questa configurazione

- **Schema Registry / Avro**: i messaggi restano JSON con schema embedded
  (pesante, ma leggibile — scelta rimandata a Fase 3).
- **Credenziali in chiaro** nel file di config: accettabile per uno stack
  locale/portfolio, non per produzione (vedi README, sezione Known
  Limitations) — in produzione si userebbe il `FileConfigProvider` di Kafka
  Connect o un secret manager esterno.
- **CDC su più tabelle** (`users`, `order_items`, `outbox_events`): Fase 1.
