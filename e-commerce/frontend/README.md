# Warehouse OS — Frontend

Frontend React per il sistema di gestione magazzino / ordini.

## Struttura

```
src/
├── api/                  # Client HTTP e chiamate auth
│   ├── client.js         # Fetch wrapper con JWT e error handling
│   └── auth.js           # Login / Register
├── context/              # React Context providers
│   ├── AuthContext.jsx    # Autenticazione e ruoli
│   └── ToastContext.jsx   # Notifiche toast
├── hooks/
│   └── useApi.js         # Hook per GET/POST/PUT/DELETE autenticati
├── components/
│   ├── ui/               # Componenti UI riusabili
│   │   ├── Btn.jsx
│   │   ├── Input.jsx
│   │   ├── TextArea.jsx
│   │   ├── Badge.jsx
│   │   ├── Card.jsx
│   │   ├── Table.jsx
│   │   ├── Pagination.jsx
│   │   ├── Modal.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── PageHeader.jsx
│   │   ├── Loading.jsx
│   │   └── index.js      # Barrel export
│   └── layout/
│       ├── Sidebar.jsx
│       └── AppLayout.jsx
├── pages/
│   ├── LoginPage.jsx
│   ├── ProductsPage.jsx
│   ├── InventoryPage.jsx
│   └── OrdersPage.jsx
├── styles/
│   ├── global.css
│   └── theme.js
├── App.jsx               # Router
└── main.jsx              # Entry point
```

## Setup

```bash
npm install
npm run dev
```

Il dev server parte su `http://localhost:5173` con proxy verso il backend su `http://localhost:8085`.

## Configurazione

- **Backend URL**: configurato nel proxy di Vite (`vite.config.js`) e in `src/api/client.js`
- **Warehouse di default**: `00000000-0000-0000-0000-000000000001` in `src/api/client.js`

## Ruoli

- **CUSTOMER**: vede prodotti, inventario, i propri ordini. Può creare ordini e pagare.
- **ADMIN**: tutto il CRUD su prodotti/inventario + gestione stato ordini (processa, spedisci, consegna).
