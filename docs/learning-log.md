# Learning log

Una voce per sessione di lavoro, non per ogni piccola cosa. Formato fisso,
~10 righe: cosa non funzionava, cosa è stato provato, perché la soluzione
funziona (o non funziona ancora). Ordine: più recente in cima.

Il punto di questo file non è documentare il progetto — per quello ci sono
il codice e `ROADMAP.md`. Il punto è avere, pronta, la versione raccontabile
in colloquio di ogni failure reale incontrato: "ho avuto un bug/incidente X,
la causa vera era Y, l'ho scoperto isolando Z" è una risposta che una
definizione da manuale non sostituisce. Vedi "Modalità di lavoro" in
[ROADMAP.md](../ROADMAP.md).

Template per una nuova voce:

```
## AAAA-MM-GG — Titolo breve

**Non funzionava:** ...
**Ho provato:** ...
**Perché funziona:** ...
**Domanda da colloquio collegata:** ...
```

---

## 2026-09-02 — EventRouter di Debezium: il task può morire mentre il connector dice RUNNING

**Non funzionava:** Il connector Debezium risultava `connector.state:
"RUNNING"`, ma sul topic `outbox.event.Order` non arrivava mai nessun
messaggio — nonostante una riga vera fosse già presente in `outbox_events`
(verificato con una query diretta su Postgres) e la config del connector,
riletta via API, fosse esattamente quella prevista.

**Ho provato:** Prima di guardare i log ho controllato config e stato via
REST API (`/connectors/.../config`, `/connectors/.../status`) — tutto
sembrava a posto. Solo leggendo `docker compose logs debezium` è saltato
fuori l'errore vero: `tasks[0].state: "FAILED"`, un'eccezione mai propagata
allo stato di primo livello del connector.

**Perché funziona (ora):** La SMT `EventRouter` era configurata con
`table.field.event.timestamp: created_at`, per usare il timestamp
applicativo dell'evento. Ma con `time.precision.mode:
adaptive_time_microseconds` (già in uso dal bug #2 di Fase 0), una colonna
`TIMESTAMPTZ` come `created_at` arriva a Debezium come stringa ISO-8601, non
come `INT64` — l'unico tipo che quel campo dell'EventRouter accetta.
Rimuovere quella riga di config (l'EventRouter ricade sul proprio default,
il `ts_ms` dell'envelope CDC, sempre `INT64`) ha risolto — e al riavvio il
task ha ripreso esattamente dalla riga che l'aveva fatto crashare, senza
perderla: la posizione dello slot di replica avanza solo dopo una
produzione Kafka riuscita, mai avvenuta per quel record.

**Domanda da colloquio collegata:** "Come fai a sapere se un connector Kafka
Connect sta funzionando davvero?" — con un incidente vero alle spalle:
`connector.state` da solo non basta, dice solo che la configurazione è
stata accettata; il task sottostante può essere morto e va controllato a
parte (`tasks[0].state` + `trace`), perché un'eccezione in una SMT può
uccidere l'intero task senza che il livello sopra lo segnali.

Nella stessa sessione, un secondo problema più sottile trovato ispezionando
Bronze dopo il fix: `REPLICA IDENTITY DEFAULT` (l'impostazione di default di
Postgres) lascia `before` completamente `null` su ogni UPDATE, perché il WAL
logga solo la PK della riga precedente. Dettaglio e fix in
[ADR 005](adr/005-replica-identity-full.md).

---

## 2026-08-26 — Repository git dentro OneDrive: timeout che sembravano bug

**Non funzionava:** `git filter-repo` per bonificare la history (email
aziendali negli autori) falliva a metà con `unable to append to
'.git/logs/refs/heads/dev': Operation timed out`, lasciando `main` riscritto
e `dev`/`main-PC6467` no — history incoerente tra branch. Anche `git fsck`
smetteva di funzionare (`mmap failed: Operation timed out`) su un repo di
soli 6 MB, dove qualunque timeout dovrebbe essere impossibile.

**Ho provato:** timeout più lunghi sui singoli comandi, `pack.threads=1`
per escludere un problema di concorrenza, disabilitare il sandbox del tool
per escludere che fosse quello a bloccare le syscall. Nessuno ha cambiato
l'esito — segno che la causa non era né il comando né l'ambiente di
esecuzione, ma qualcosa di esterno a entrambi.

**Perché funziona:** la cartella di lavoro vive dentro OneDrive (Files
On-Demand). `.git/objects/` è il caso peggiore possibile per un filesystem
virtualizzato — migliaia di file minuscoli invece di uno grande — e ogni
accesso può comportare un'idratazione cloud invece di una lettura locale.
Riprovando la stessa identica operazione in un clone su disco locale: 0.48
secondi invece del timeout. Non era un bug, era la variabile ambientale.
Backup (`git bundle`) fatto *prima* di scoprirlo si è rivelato decisivo:
ha permesso di ripartire da uno stato pulito invece di riparare quello
corrotto a metà.

**Domanda da colloquio collegata:** "Hai mai diagnosticato un problema che
sembrava un bug e non lo era? Come hai isolato la vera variabile?" — la
risposta qui è concreta: cambiare *una sola cosa alla volta* (stessa
history, stesso comando, cartella diversa) fino a trovare quella che
cambiava l'esito, invece di continuare a modificare il comando che sembrava
sospetto.
