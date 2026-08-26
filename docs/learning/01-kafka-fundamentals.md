# Lab 1 — Kafka: solo i concetti che la tua pipeline usa davvero

**Tempo:** 2-3 ore. **Prerequisito:** `docker compose up -d kafka` (Kafka UI su http://localhost:8080).

Ogni sezione ha un blocco **Predici**. Scrivi la risposta *prima* di eseguire il
comando, anche se ti sembra ovvia. La distanza tra la tua predizione e l'esito è
l'unica cosa che stai imparando qui: se salti le predizioni, questo lab diventa
copia-incolla e non serve a niente.

Alla fine ci sono 8 domande di autovalutazione. Sono, letteralmente, domande da
colloquio.

---

## 0. Setup

Tutti i comandi girano dentro il container `kafka` (il listener interno risponde
su `localhost:9092` dall'interno del container):

```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

Se questo comando risponde (anche con una lista vuota), sei pronto.

---

## 1. Topic, partizioni, offset

**Concetto.** Un topic è un log append-only diviso in *partizioni*. Ogni partizione
è una sequenza ordinata di record, ognuno identificato da un numero progressivo:
l'*offset*. L'ordine è garantito **solo dentro una partizione**, mai fra partizioni
diverse. Questa singola frase è la causa del 90% dei bug di ordering nelle pipeline CDC.

**Predici.** Creo un topic con 3 partizioni e ci scrivo 6 messaggi senza chiave.
Quanti messaggi finiranno in ciascuna partizione? Scrivi la tua risposta.

**Esegui.**

```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic lab-basics --partitions 3 --replication-factor 1
```

```bash
docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic lab-basics <<< $'m1\nm2\nm3\nm4\nm5\nm6'
```

```bash
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic lab-basics --from-beginning --timeout-ms 5000 --property print.partition=true --property print.offset=true
```

**Osserva.** Probabilmente tutti i messaggi sono nella *stessa* partizione, non
distribuiti 2/2/2. Dalla 2.4 il producer usa lo *sticky partitioning*: senza chiave,
riempie una partizione per batch invece di fare round-robin per record — meno
richieste di rete, batch più grossi. Non è casualità: è un'ottimizzazione.

**Perché conta.** L'assenza di chiave significa assenza di garanzie di ordine
utili. Se in futuro producessi eventi derivati senza chiave, non potresti più
ricostruire la sequenza di modifiche di una riga.

---

## 2. La chiave decide la partizione — il concetto #1 per la CDC

**Concetto.** Con una chiave, il producer calcola `murmur2(key) % numPartitions`.
Deterministico: la stessa chiave finisce **sempre** nella stessa partizione, quindi
i suoi messaggi sono **ordinati fra loro**. Debezium usa la primary key della riga
come chiave del messaggio: tutte le modifiche dell'ordine `abc-123` viaggiano
nella stessa partizione, nell'ordine in cui sono avvenute nel database.

**Predici.** Scrivo 6 messaggi con solo 2 chiavi distinte (`a` e `b`), alternate.
In quante partizioni finiranno? E l'ordine dei messaggi con chiave `a` è garantito?

**Esegui.**

```bash
docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic lab-basics --property parse.key=true --property key.separator=: <<< $'a:1\nb:1\na:2\nb:2\na:3\nb:3'
```

```bash
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic lab-basics --from-beginning --timeout-ms 5000 --property print.key=true --property print.partition=true
```

**Osserva.** Tutti gli `a` in una partizione, tutti i `b` in un'altra (o nella
stessa, se l'hash collide — succede e non è un bug). Dentro ogni partizione,
`1 → 2 → 3` in ordine.

**Ora il pezzo importante.** Aumenta le partizioni da 3 a 6:

```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --alter --topic lab-basics --partitions 6
```

Riscrivi `a:4` e osserva in quale partizione finisce. `murmur2("a") % 3` e
`murmur2("a") % 6` sono numeri diversi: **la chiave `a` cambia partizione**. I suoi
messaggi vecchi restano dove erano, i nuovi vanno altrove, e l'ordine fra vecchi e
nuovi non è più garantito da niente.

**Perché conta.** È esattamente il motivo per cui, in una pipeline CDC, non si
cambia il numero di partizioni di un topic a caldo senza un piano. È anche una
domanda da colloquio molto frequente, e la risposta "si perde l'ordering per le
chiavi esistenti" ti distingue immediatamente.

---

## 3. Consumer group, commit, lag

**Concetto.** Un *consumer group* è un insieme di consumer che si dividono le
partizioni: ogni partizione è assegnata a **un solo** consumer del gruppo. Il gruppo
tiene traccia, per ogni partizione, dell'offset fino a cui ha *committato* il lavoro.
Il **lag** è la distanza tra l'ultimo offset prodotto e l'ultimo committato: quanto
sei indietro.

**Predici.** Un gruppo con 1 consumer su un topic a 6 partizioni: quante partizioni
riceve? E se avvio un secondo consumer nello stesso gruppo? E un terzo su 2 partizioni?

**Esegui.** Consuma con un gruppo e fermalo (Ctrl-C o timeout):

```bash
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic lab-basics --from-beginning --timeout-ms 5000 --group lab-group
```

```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group lab-group --describe
```

**Osserva.** La colonna `LAG` per ogni partizione: `CURRENT-OFFSET` (dove è arrivato
il gruppo) contro `LOG-END-OFFSET` (dove è arrivato il producer). Produci altri
messaggi senza consumare e ri-esegui il `--describe`: vedi il lag crescere.

**Perché conta.** In fase 7 il lag del consumer group è la metrica di allarme
principale della pipeline. Ed è la metrica che il README del progetto già promette
in Grafana — oggi senza averla.

---

## 4. Replay: il reset degli offset

**Concetto.** Gli offset committati sono un dato mutabile: puoi riportarli indietro
e far rileggere al consumer messaggi già processati. È il meccanismo alla base
dell'obiettivo 8 (reprocessing e backfill), e funziona solo se i messaggi sono
ancora nel topic (vedi retention, sezione 5).

**Predici.** Se riporto gli offset del gruppo a `earliest` e riavvio il consumer,
cosa vedo? E se il mio consumer scrivesse su un database, cosa succederebbe a quei
record?

**Esegui.** Sempre prima in `--dry-run`:

```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group lab-group --topic lab-basics --reset-offsets --to-earliest --dry-run
```

```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group lab-group --topic lab-basics --reset-offsets --to-earliest --execute
```

Poi prova il reset per timestamp, che è quello che userai davvero nei backfill
(formato `YYYY-MM-DDTHH:mm:ss.SSS`):

```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group lab-group --topic lab-basics --reset-offsets --to-datetime 2026-01-01T00:00:00.000 --dry-run
```

**Osserva.** Prova a fare `--execute` **mentre** un consumer del gruppo è attivo:
fallisce. Il reset richiede che il gruppo non abbia membri attivi — Kafka non ti
lascia spostare il terreno sotto i piedi di un consumer in esecuzione.

**Perché conta.** Il tuo runbook di backfill (fase 5) sarà costruito su questi
comandi. E la seconda domanda della predizione — cosa succede ai record già
scritti nel database — è esattamente il problema che la fase 4 (idempotenza dei
sink) esiste per risolvere. Se il replay duplica i dati, il replay è inutilizzabile.

---

## 5. Retention vs compaction, e perché Debezium emette i tombstone

**Concetto.** Due politiche di pulizia, con scopi opposti:

- `cleanup.policy=delete` (default): butta via i segmenti più vecchi di
  `retention.ms`. Il log è una finestra temporale.
- `cleanup.policy=compact`: conserva **l'ultimo valore per ogni chiave**, per
  sempre. Il log diventa uno snapshot dello stato corrente.

In un topic compattato, come si cancella una chiave? Con un record dal valore
**null**: il *tombstone*. La compaction lo interpreta come "questa chiave non
esiste più" e, dopo `delete.retention.ms`, rimuove sia il tombstone sia i valori
precedenti.

**Predici.** Debezium, quando cancelli una riga, emette **due** messaggi: un evento
con `op: "d"` e un tombstone con valore null. Perché due? A cosa serve il secondo,
dato che il primo già dice che la riga è stata cancellata?

**Esegui.**

```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic lab-compact --partitions 1 --replication-factor 1 --config cleanup.policy=compact --config min.cleanable.dirty.ratio=0.01 --config segment.ms=1000 --config delete.retention.ms=100
```

Verifica se la tua versione del console producer sa produrre valori null:

```bash
docker exec kafka kafka-console-producer --help 2>&1 | grep -i null
```

Se compare `null.marker`, puoi produrre un tombstone così (chiave `k1`, valore null):

```bash
docker exec -i kafka kafka-console-producer --bootstrap-server localhost:9092 --topic lab-compact --property parse.key=true --property key.separator=: --property null.marker=NULL <<< $'k1:v1\nk2:v2\nk1:v2\nk1:NULL'
```

**Osserva.** Rileggi il topic con `print.key=true`: all'inizio vedi tutta la storia.
La compaction gira in background e non è istantanea — serve che il segmento ruoti,
quindi produci qualche altro messaggio e attendi un minuto prima di rileggere.
Alla fine `k1` sparisce e di `k2` resta solo l'ultimo valore.

**Perché conta.** Due cose, entrambe già dentro il tuo repo. Primo: il tombstone
esiste perché un topic compattato possa *dimenticare* una riga cancellata — è anche
il meccanismo con cui implementerai la cancellazione GDPR. Secondo: il tuo
[cdc_bronze.py](../../spark_apps/cdc_bronze.py) fa `from_json` sul valore senza
controllare se è null, quindi ogni tombstone diventa una **riga interamente null**
appesa in Bronze. Ora sai esattamente perché quel bug esiste e cosa lo genera.

---

## 6. Durabilità: acks, ISR, idempotenza del producer

**Concetto.** Quando un producer scrive, `acks` decide quando considerare l'ack:
`0` (mai aspettare), `1` (solo il leader ha scritto), `all` (tutte le replica
in-sync hanno scritto). Con `acks=all` + `min.insync.replicas=2` + replication
factor 3 sopravvivi alla perdita di un broker senza perdere dati.

Un producer *idempotente* (`enable.idempotence=true`) aggiunge un sequence number
per partizione: se un retry duplica una richiesta, il broker la scarta. Elimina i
duplicati causati dai retry di rete — **non** i duplicati applicativi.

**Il limite del tuo setup locale.** Hai un solo broker e replication factor 1:
`acks=all` è indistinguibile da `acks=1`, e nessuna configurazione ti protegge dalla
perdita di quel broker. Non è un difetto del lab, è un vincolo da **dichiarare
esplicitamente** nel README: sapere quale garanzia il tuo ambiente *non* può dare
è un segnale di maturità, fingere il contrario è il contrario.

**Perché conta.** È il vocabolario della fase 4. "At-least-once" e "exactly-once"
senza `acks`, ISR e idempotenza sotto sono slogan.

---

## Pulizia

```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic lab-basics --topic lab-compact
```

---

## Autovalutazione

Rispondi a voce alta, senza rileggere. Se una risposta esce esitante, torna alla
sezione. Su queste ti interrogherò prima di iniziare la fase 1.

1. Perché Debezium usa la primary key della riga come chiave del messaggio Kafka?
2. Hai un topic CDC a 3 partizioni e lo porti a 6. Cosa si rompe, e per quali righe?
3. Che differenza c'è tra `CURRENT-OFFSET` e `LOG-END-OFFSET`? Cos'è il lag?
4. Un consumer muore dopo aver processato 100 messaggi ma prima di committare.
   Cosa succede quando il gruppo si riequilibra? Quanti messaggi vengono processati
   due volte?
5. Perché la compaction ha bisogno dei tombstone, e perché un `op: "d"` non basta?
6. Il tuo job Spark muore a metà micro-batch: cosa è già stato scritto in Delta e
   cosa verrà riletto da Kafka al riavvio?
7. Perché `--reset-offsets --execute` fallisce se il consumer group ha membri attivi?
8. `acks=all` su un cluster con replication factor 1: quale garanzia ti dà davvero?
