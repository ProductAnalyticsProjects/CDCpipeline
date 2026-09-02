# ADR 005 — REPLICA IDENTITY FULL sulle quattro tabelle CDC (`V5__set_replica_identity_full.sql`)

## Failure

Con `REPLICA IDENTITY` a `DEFAULT` (l'impostazione di default di Postgres,
verificata su tutte e quattro le tabelle via `pg_class.relreplident`), il WAL
logga per un UPDATE/DELETE solo la primary key della riga precedente, non
l'intera riga. Lo schema di `before` che Debezium costruisce richiede però
tutte le colonne — con solo la PK disponibile non può popolarlo, e lo lascia
`null` per intero.

Osservato dal vivo durante il rompilo di Fase 1, non solo previsto a tavolino:
l'ordine e2e (`96c74ce5-...`), cancellato ~20 minuti dopo la creazione da
`ReservationCleanupJob` (timeout della reservation, mai pagato). Il messaggio
arrivato in Bronze ha `cdc_op: "u"`, `after.status: "CANCELLED"` — ma
`before: null`, nonostante fosse un update vero con uno stato precedente
(`PENDING`) perfettamente noto a Postgres un istante prima.

## Come funziona la fix

`ALTER TABLE ... REPLICA IDENTITY FULL` sulle 4 tabelle (`orders`, `users`,
`order_items`, `outbox_events`) — Postgres logga l'intera riga precedente nel
WAL per ogni UPDATE/DELETE, non solo la PK. Debezium può quindi popolare
`before` per intero, ripristinando la promessa di "envelope completo" della
Fase 1 anche sugli update, non solo sugli insert.

Serve anche a due obiettivi più avanti nel ROADMAP: il bonus GDPR
(propagazione del delete) ha bisogno di sapere *cosa* viene cancellato, non
solo che una riga è sparita — impossibile senza un `before` completo sulla
delete; un audit trail vero (chi ha cambiato cosa, da quale stato a quale)
richiede lo stesso prima/dopo esplicito.

## Trade-off accettato

`FULL` logga più byte nel WAL per ogni UPDATE/DELETE — l'intera riga vecchia,
non solo la PK. L'aumento è transitorio, non un accumulo permanente: quei
byte restano sul disco solo finché Debezium non li ha letti e prodotti su
Kafka, poi Postgres li ricicla come farebbe comunque. L'heartbeat non è
quello che rende `FULL` economico — è un meccanismo diverso, che impedisce a
uno slot idle di bloccare il riciclo; `FULL` scrive comunque più byte alla
fonte, a prescindere dall'heartbeat.

L'impatto reale è concentrato su una sola tabella. `outbox_events` è
insert-only per costruzione (`OutboxService.publish()` non fa mai update o
delete su quella tabella): `REPLICA IDENTITY` incide solo su quelle due
operazioni, quindi su questa tabella `FULL` costa zero byte in più rispetto a
`DEFAULT`. `order_items` è nella pratica lo stesso caso (le righe non vengono
più toccate dopo la creazione dell'ordine). `users` cambia raramente. `orders`
è l'unica tabella con update frequenti (le transizioni di stato) — ed è anche
l'unica dove il costo di `FULL` è realmente diverso da zero, restando
comunque trascurabile alla scala di questo progetto.
