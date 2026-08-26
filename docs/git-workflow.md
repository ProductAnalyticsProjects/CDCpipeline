# Flusso git — stato attuale e target production-ready

Verificato il 26 agosto 2026 sul repo `ProductAnalyticsProjects/CDCpipeline`
(**pubblico**, default branch `main`, creato il 2 gennaio 2026).

**Aggiornamento 26 agosto 2026 (identità):** l'identità autore è stata
sistemata nella stessa sessione in cui è stato scritto questo documento —
history riscritta con `git filter-repo --mailmap`, force-push su `main` e
`dev` con `--force-with-lease`. Le due identità finali sono
`Pascal <89842492+Bolinmea@users.noreply.github.com>` e
`AlessioNovi <20397368+AlessioNovi@users.noreply.github.com>`.

**Aggiornamento 26 agosto 2026 (data/ e branch stale):** rimosso `data/`
dall'intera history con `git filter-repo --invert-paths --path data/` —
`.git` è passato da ~6 MB a 440 KB. Un commit (`Delete data directory`) è
stato scartato perché, senza `data/`, restava vuoto: nessuna perdita reale,
solo un no-op che non aveva più contenuto da rappresentare. `dev` è stato
archiviato come tag `archive/dev` e cancellato dal remote; `main-PC6467` non
è mai esistito su GitHub, resta solo locale. Il repo ha ora un solo branch
remoto: `main`.

Il resto di questo documento (Blocchi 1, 3, 4) descrive ancora lavoro da fare.

---

## Stato attuale

| Cosa | Stato | Evidenza |
|---|---|---|
| CI con 6 job su push e PR | ✅ | `.github/workflows/ci.yml` |
| Build Docker separata, push su GHCR solo da main | ✅ | `.github/workflows/docker-build.yml` |
| pre-commit con ruff + hook base | ✅ | `.pre-commit-config.yaml` |
| Script di branch protection scritto e ben ragionato | ✅ | `scripts/setup-branch-protection.sh` |
| **Branch protection attiva** | ❌ | `gh api .../branches/main/protection` → `404 Branch not protected`. Lo script esiste ma non è mai stato eseguito. |
| **Flusso a PR** | ❌ | `gh pr list --state all` → **zero PR nella storia del repo**. Tutto in push diretto su `main`. |
| LICENSE | ❌ | Il README dichiara MIT, ma `licenseInfo: null`: GitHub non mostra alcuna licenza nella sidebar |
| **Repo gonfiato da dati di runtime** | ✅ | Fatto il 26/08: `git filter-repo --invert-paths --path data/`. `.git` da 6 MB a 440 KB. |
| Tag / release / CHANGELOG | ❌ | `git tag` vuoto |
| Branch puliti | ✅ | Fatto il 26/08: `dev` archiviato come tag `archive/dev` e cancellato dal remote. Un solo branch remoto: `main`. |
| Identità autore coerenti | ✅ | Fatto il 26/08: `git filter-repo --mailmap` + force-push. Due identità pulite, 34 commit ciascuna. |
| Convenzione commit | ❌ | Lingue e stili mescolati: pochi `feat:`/`chore:`, molti messaggi descrittivi in italiano, alcuni commit multi-scopo |
| Secret scanning | ❌ | Nessun gate. In history c'è `MINIO_SECRET` hardcoded, rimosso in `b4914b6` (valore: `minioadmin`, credenziale di default) |
| PR template / CODEOWNERS / dependabot | ❌ | `.github/` contiene solo `workflows/` |
| `.gitattributes` | ❌ | Assente: nessuna normalizzazione dei fine riga |
| `permissions:` least-privilege nei workflow | ❌ | `ci.yml` non dichiara `permissions` a livello top |
| Immagini Docker pinnate | ❌ | `minio:latest`, `grafana:latest`, `kafka-ui:latest`, `pgadmin4` → build non riproducibili |

**Conseguenza pratica dello stato attuale:** la CI gira ma non protegge niente.
Un push con i test rossi entra su `main` senza attriti. In un colloquio, "ho una
CI con sei job" e "ho una CI con sei job obbligatori prima del merge" sono due
affermazioni molto diverse, e la seconda è verificabile da chiunque apra il repo.

---

## Il flusso target: trunk-based con PR brevi

`main` sempre verde e deployabile. Ogni cambiamento passa da un branch a vita
breve (ore o giorni, non settimane) e da una PR che i check devono approvare.
Squash merge, così `main` ha un commit per unità di lavoro. Tag semver a fine
di ogni fase della roadmap.

**Perché non GitFlow** (develop + release/* + hotfix/*): GitFlow è nato per
software con release versionate e più versioni supportate in parallelo. Con uno
o tre maintainer e deploy continuo aggiunge cerimonia — merge in due direzioni,
branch di lunga vita che divergono — senza ridurre alcun rischio reale. Il
branch `dev` fermo da quattro mesi in questo repo è esattamente il modo in cui
GitFlow degenera quando non c'è il contesto che lo giustifica.

Saper dire *quale* flusso si adatta al contesto, e perché, vale più che
recitare GitFlow a memoria: è una domanda da colloquio frequente.

---

## Blocco 1 — `main` protetta e flusso PR (~1h)

### La trappola nello script attuale

`scripts/setup-branch-protection.sh` imposta
`required_approving_review_count=1` insieme a `enforce_admins=true`. **GitHub
non permette di approvare la propria pull request.** Su un repo con un solo
maintainer, quella combinazione rende il merge *impossibile*: nessuno può dare
l'approvazione richiesta e, con `enforce_admins=true`, nemmeno tu puoi
scavalcare la regola.

Da correggere prima di eseguirlo:

- `required_approving_review_count=0` — la qualità la garantiscono i check
  obbligatori, non un'approvazione che ti daresti da solo
- lasciare un commento nello script: in un team il valore giusto è 1, ed è la
  prima cosa da cambiare quando arriva un secondo contributore
- `required_linear_history=true`, coerente con il squash merge

Il resto dello script è corretto, incluso il ragionamento sull'esclusione del
job `docker`: un required check con filtro `paths:` non viene creato sulle PR
che non toccano quei file, e blocca il merge per sempre. È la trappola più
comune nella configurazione delle branch protection.

### Impostazioni repo

- squash merge come unica opzione (disattivare merge commit e rebase merge)
- "Automatically delete head branches" attivo
- `.github/pull_request_template.md`: cosa cambia, quale fase della roadmap,
  come è stato verificato, quale failure mode copre

### Il loop di lavoro

```bash
git switch -c feat/fase0-db-unico
# ... lavoro, commit ...
git push -u origin feat/fase0-db-unico
gh pr create --fill
# check verdi →
gh pr merge --squash --delete-branch
```

Naming: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/` + riferimento alla fase.

---

## Blocco 2 — Igiene della history (~1h)

**Branch stale.** `dev` e `main-PC6467` non servono più ma contengono storia.
Archiviarli come tag e cancellare i branch, così restano recuperabili senza
comparire nella lista dei branch di chi apre il repo:

```bash
git tag archive/dev dev && git push origin archive/dev && git push origin --delete dev
```

**Identità autore: il repo ha quattro identità, non due.**

```
34  anovi   <anovi@gualaclosures.come>
30  Pascal  <pdigirolamo@gualaclosures.com>
 3  Bolinmea <pascal.digirolamo@outlook.com>
 1  Bolinmea <89842492+Bolinmea@users.noreply.github.com>
```

`anovi` è un contributore reale: **la history non si riscrive** e la sua
attribuzione non si tocca. Riscriverla su un repo usato come portfolio
significherebbe attribuirsi codice di qualcun altro.

Le altre tre sono tutte Pascal, con `user.email` diverso su macchine diverse.
Consolidarle con un `.mailmap` è legittimo — nessuna riattribuzione, solo la
stessa persona sotto un nome — e fa sì che `git shortlog` dica la verità:

```
Pascal Di Girolamo <pdigirolamo@gualaclosures.com> Bolinmea <pascal.digirolamo@outlook.com>
Pascal Di Girolamo <pdigirolamo@gualaclosures.com> Bolinmea <89842492+Bolinmea@users.noreply.github.com>
```

**Attribuzione nel README (importante, e a costo zero).** La divisione del
lavoro nella history è netta:

| Area | Autore prevalente |
|---|---|
| `e-commerce/backend/` (176 file toccati), `e-commerce/frontend/` (32) | **anovi** |
| `spark_apps/`, `dbt_project/`, `trino/`, `great_expectations/`, `dags/`, `.github/` | **Pascal** |

Cioè: l'applicazione che *genera* gli eventi è in larga parte di anovi, la
pipeline CDC che li *consuma* è di Pascal. Dichiararlo in una sezione
"Contributi" del README **aumenta** la credibilità invece di ridurla: un
revisore che vede due contributori e nessuna spiegazione si chiede chi abbia
scritto cosa, e nel dubbio assume il peggio.

Ha anche una conseguenza pratica in colloquio: il pattern outbox nel backend
(`OutboxService`, `OutboxEvent`, la migrazione `V4`) è codice di anovi. Va
saputo, perché se l'intervistatore ci si sofferma la risposta onesta è "quella
parte l'ha scritta il mio collega, io ci ho costruito sopra l'EventRouter" —
che è una risposta forte, mentre farsi trovare a improvvisare su codice non
proprio è l'unico modo di uscirne male.

**Review richieste, di conseguenza.** Se anovi è ancora attivo sul progetto,
`required_approving_review_count=1` è la scelta giusta ed è il momento di
aggiungere un `.github/CODEOWNERS` (backend → anovi, pipeline → Pascal). Se non
lo è più, resta 0: meglio zero review che un repo in cui non puoi mergiare.

**LICENSE.** Il README dichiara MIT ma il file non esiste, quindi GitHub non
mostra licenza: legalmente il codice è "tutti i diritti riservati" e chiunque
lo trovi non sa se può usarlo. Aggiungere `LICENSE` con il testo MIT: due minuti.

**`.gitattributes`.** Normalizzazione dei fine riga (`* text=auto`), `*.jar
binary`, e `linguist-vendored` sul frontend così GitHub non classifica il repo
come progetto JavaScript.

**File di runtime committati per errore (data/) — il cleanup più grosso di questo blocco.**

```
740 blob distinti, 561.7 MB logici totali
data/zookeeper/log/version-2/log.*   6 file × 64 MB  (i soli che GitHub segnala: > 50 MB)
data/kafka/**/*.{index,timeindex,log}  decine di file × 10-16 MB
data/postgres/pg_wal/*                 3 file × 16 MB
```

Introdotti nei primissimi commit (9 gennaio 2026), prima che `.gitignore`
escludesse `data/`. Il motivo per cui il pack locale resta piccolo (`du -sh .git`
≈ 6 MB) mentre GitHub avvisa di file da 64 MB: sono segmenti Kafka/Zookeeper/WAL
preallocati, in gran parte spazio vuoto — comprimono benissimo con zlib, ma
GitHub controlla la dimensione **logica** (pre-compressione) del blob, non
quella compressa. `data/` è già correttamente in `.gitignore`: è solo zavorra
storica, nessun rischio attivo — ma è il tipo di cosa che fa una pessima
impressione a chi clona un repo che si dichiara "production ready".

```bash
git filter-repo --force --invert-paths --path data/
```

Stessa famiglia di operazione della riscrittura per l'identità autore (vedi
sopra): rewrite di tutti gli hash + force-push su `main` e `dev`. **Da fare
nella stessa sessione di lavoro della fase 0.5**, non come rewrite separato —
ogni riscrittura di history su questo repo richiede un force-push e un
re-clone della copia locale (vedi nota sotto su OneDrive), quindi conviene
accorpare tutte le riscritture previste in un solo passaggio invece di pagare
il costo più volte.

**Nota operativa — OneDrive.** La cartella di lavoro locale vive in una
cartella sincronizzata OneDrive. Operazioni pesanti su `.git/` (`pack-objects`,
`filter-repo`, `fsck`) possono avere timeout intermittenti lì. Il modo
affidabile: fare il rewrite in un clone temporaneo su disco locale veloce,
verificare (`git fsck`, `git shortlog`), poi pushare da lì e infine ri-clonare
pulito dentro OneDrive — non tentare il rewrite in place.

**Remote.** Si chiama `docker` invece di `origin` — funziona, ma ogni comando
copiato da un tutorial va tradotto. `git remote rename docker origin`.

**`CICD_SETUP.md`.** È un documento di handoff ("copia questa cartella sopra la
tua copia locale", con riferimenti ai tuoi CV), non documentazione del repo. Il
contenuto tecnico è buono: va riscritto come `docs/ci-cd.md` in terza persona.

---

## Blocco 3 — Gate automatici (~1.5h)

| Gate | Dove | Cosa intercetta |
|---|---|---|
| **gitleaks** | pre-commit + job CI | Secret prima che entrino in history. Il controllo che manca oggi. |
| **commitlint** (conventional commits) | pre-commit `commit-msg` | Messaggi coerenti, e abilita il CHANGELOG generato |
| **hadolint** | pre-commit | `dockerfile`: mismatch di versione, layer non ottimali |
| **shellcheck** | pre-commit | `scripts/*.sh`, `spark_apps/*.bash` — bug di quoting che si manifestano solo con path con spazi |
| **sqlfluff** | pre-commit | I modelli dbt, oggi non lintati da niente |
| `check-json`, `check-merge-conflict`, `detect-private-key` | pre-commit | Le suite GE sono JSON scritti a mano |
| **dependabot** | `.github/dependabot.yml` | Versioni delle GitHub Actions e delle dipendenze pip |
| `permissions: contents: read` | top-level di entrambi i workflow | Least privilege: oggi i job hanno il token con permessi di default |
| `concurrency` | `docker-build.yml` | Presente in `ci.yml`, manca qui |
| Pin delle immagini `:latest` | `docker-compose.yaml` | Riproducibilità: oggi `docker compose pull` può cambiarti lo stack sotto i piedi |

---

## Blocco 4 — Versionamento e release (~0.5h)

- **Tag semver a fine fase**: `v0.1.0` = fase 0 chiusa, `v0.2.0` = fase 1, e
  così via. Dà a chi guarda il repo un modo di vedere il progetto come una
  progressione, non come un blob di commit.
- **CHANGELOG.md** in formato keep-a-changelog, generabile dai conventional
  commits.
- **GitHub Release** per ogni tag, con note che dicono cosa quella fase ha
  reso possibile: per un recruiter è la storia del progetto in forma leggibile.
- **Immagine Docker taggata con la versione**, non solo `latest` e sha: oggi
  `docker-build.yml` pubblica `spark:latest` e `spark:<sha>`, e `latest` su un
  registry pubblico è irriproducibile per definizione.

---

## Cosa deliberatamente NON facciamo

**GitFlow** — vedi sopra: cerimonia senza riduzione di rischio a questa scala.

**Firma GPG obbligatoria dei commit** — sensata dove conta chi ha scritto cosa
(supply chain, repo con molti contributori). Su un portfolio a un maintainer il
costo di setup supera la resa, e nessun revisore te la conterà come punto a
favore. Da saper spiegare, non da implementare ora.

**Riscrivere la history per il secret** — il valore trovato è `minioadmin`, la
credenziale di default pubblica di MinIO: non è un segreto, è un placeholder.
Riscrivere la history invaliderebbe tutti gli hash per bonificare un non-segreto.
Ciò che serve è il **gate** (gitleaks), non la bonifica.

Il runbook per un segreto **vero**, invece, è: (1) ruotare la credenziale
immediatamente — dal momento in cui è stata pushata su un repo pubblico va
considerata compromessa, i bot che scansionano GitHub sono più veloci di te;
(2) solo dopo riscrivere la history; (3) invalidare i clone esistenti. In
quest'ordine: riscrivere prima di ruotare dà solo l'illusione di aver risolto.

**Release automation** (semantic-release e simili) — overkill a un maintainer.
Un tag e delle note scritte a mano per fase sono più curati e costano meno.

---

## Domande da colloquio che questo blocco copre

1. Che flusso git usavate, e perché quello? Perché non GitFlow?
2. Cosa fai se ti accorgi di aver pushato un secret su un repo pubblico? In che ordine?
3. Cos'è un required status check che diventa una trappola? (suggerimento: filtri `paths:`)
4. Squash merge, merge commit o rebase: quando useresti quale?
5. Perché `main` protetta con "1 review richiesta" può bloccare un repo a maintainer singolo?
6. Cosa rende una build riproducibile, e cosa la rompe in questo repo?
