# ADR 001 — Configurazione del connector Debezium (`debezium/connectors/ecommerce.json`)

> Scritto in Fase 0, quando il file si chiamava `orders.json` e copriva solo
> `public.orders`. Dalla Fase 1 il connector copre quattro tabelle e il file è
> `ecommerce.json`; le scelte descritte qui valgono invariate. I bug #1-#3
> citati sotto sono tutti risolti: ogni sezione ha una riga **Stato**.

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

**Il più importante di questa lista.** Il caso pericoloso non è un
database del tutto inattivo, ma **tabelle catturate inattive mentre il resto
del database continua a scrivere**: il WAL cresce per le altre tabelle, ma il
connector non riceve nessun evento e quindi non conferma mai un
`confirmed_flush_lsn` più recente. Postgres non può riciclare i segmenti WAL
più vecchi di quel punto, perché "potrebbero ancora servire al consumer
collegato allo slot", e il WAL cresce finché il disco non si riempie. È
l'incidente da manuale per chi opera CDC in produzione. L'heartbeat manda un
messaggio periodico anche senza modifiche sulle tabelle catturate, e fa
avanzare comunque l'offset confermato. Se non bastasse (per esempio con
publication filtrate che non vedono mai traffico), la leva successiva è
`heartbeat.action.query`, che genera una scrittura vera su una tabella
dedicata inclusa nella publication.

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

**Stato:** risolto in Fase 0 (PR #32) — `convert_base_to_decimal` in
`spark_apps/bronze_transforms.py` produce la colonna `<nome>_decoded`.

## `time.precision.mode: adaptive_time_microseconds`

Dichiarato esplicitamente per non dipendere dal default della versione
installata (già cambiato una volta tra major di Debezium). Per una colonna
`TIMESTAMPTZ` come `created_at`/`updated_at`, Debezium emette comunque una
stringa ISO-8601 con offset — questo parametro incide soprattutto su
`TIME`/`TIMESTAMP WITHOUT TIME ZONE`, non elimina il **bug #2**: lo schema
di `cdc_bronze.py` dichiarava quelle colonne `LongType` aspettandosi epoch
numerico, quando invece arriva una stringa. Anche questo era un fix Spark,
non di connector.

**Stato:** risolto in Fase 0 (PR #36) — `TimestampType` in Bronze,
`TIMESTAMP(6)` nello schema Trino, `CAST(created_at AS DATE)` nei modelli Gold.

## `tombstones.on.delete: true` (il default, dichiarato esplicitamente)

Per ogni delete, Debezium emette **due** messaggi: l'evento con `op: "d"`,
poi un *tombstone* — un messaggio con la stessa chiave e valore `null`. Serve
alla compaction di Kafka per sapere che quella chiave può essere dimenticata
definitivamente (vedi `docs/learning/01-kafka-fundamentals.md`, sezione 5).

In Fase 0 `cdc_bronze.py` non lo sapeva: faceva `from_json` sul valore senza
controllare se fosse null, quindi ogni tombstone diventava una riga
interamente null appesa in Bronze. **Bug #3**: la fix è filtrare (o gestire
esplicitamente) i messaggi a valore null — di nuovo, logica applicativa, non
configurazione del connector.

**Stato:** risolto in Fase 0 (PR #32) — `.na.drop(subset="cdc_op")` in
`build_bronze_df` scarta la riga tutta-null prodotta dal tombstone.

## Cosa NON è ancora coperto da questa configurazione

- **Schema Registry / Avro**: i messaggi restano JSON con schema embedded
  (pesante, ma leggibile — scelta rimandata a Fase 3).
- **Credenziali in chiaro** nel file di config: accettabile per uno stack
  locale/portfolio, non per produzione (vedi README, sezione Known
  Limitations) — in produzione si userebbe il `FileConfigProvider` di Kafka
  Connect o un secret manager esterno.
- ~~**CDC su più tabelle**~~: fatto in Fase 1 (PR #41) — `users`,
  `order_items` e `outbox_events`, quest'ultima instradata con l'EventRouter SMT.
- **`max_slot_wal_keep_size`** non configurato su Postgres: metterebbe un tetto
  al WAL trattenuto da uno slot fermo, al prezzo di invalidare lo slot (e
  dover rifare lo snapshot) quando il tetto viene superato.
