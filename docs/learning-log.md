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
