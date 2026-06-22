# Kokpit rewaluacji portfela walutowego

Aplikacja webowa przeszacowująca syntetyczne konta walutowe (EUR/USD/PLN) do PLN
po dziennych kursach NBP (tabela A, `api.nbp.pl`).

**Panel:** wykres liniowy wartości portfela w czasie + suwak „kurs ±X%", który
przelicza wartość portfela **po stronie backendu** (a nie tylko filtruje w przeglądarce).

> Projekt: mBank / Wojciech Sitek — zadanie 1. Pełne uzasadnienie stosu i decyzji
> projektowych w pliku [RAPORT.md](RAPORT.md).

---

## Stos technologiczny

| Warstwa   | Technologia                      |
|-----------|----------------------------------|
| Backend   | Python 3.10 + FastAPI + httpx    |
| Frontend  | React 18 + Vite + Recharts       |
| Dane      | plik JSON (`backend/accounts.json`) + cache kursów NBP w pamięci |
| Źródło kursów | NBP API, tabela A (`api.nbp.pl`) |

Brak bazy danych — konta trzymane są w pliku JSON, a kursy NBP cache'owane
w pamięci procesu (TTL 30 min).

---

## Uruchomienie

### 1. Backend (FastAPI, port 8000)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Sprawdzenie: <http://127.0.0.1:8000/api/health> oraz dokumentacja Swagger
pod <http://127.0.0.1:8000/docs>.

### 2. Frontend (React + Vite, port 5173)

```bash
cd frontend
npm install
npm run dev
```

Aplikacja: <http://localhost:5173>. Dev-server Vite proxuje `/api/*`
do backendu na `:8000` (konfiguracja w `vite.config.js`), więc nie trzeba
nic dodatkowo ustawiać.

---

## API

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| `GET`  | `/api/health` | Status serwisu |
| `GET`  | `/api/accounts` | Lista syntetycznych kont |
| `GET`  | `/api/portfolio?days=30&adjust=0` | Seria czasowa wartości portfela w PLN. `adjust` = korekta kursu w % (suwak); **przeliczenie wykonuje backend** |

Przykład:

```bash
curl "http://127.0.0.1:8000/api/portfolio?days=20&adjust=10"
```

---

## Struktura

```
portfolio-nbp/
├── backend/
│   ├── main.py           # FastAPI: pobieranie kursów NBP + rewaluacja
│   ├── accounts.json     # 5 syntetycznych kont (EUR/USD/PLN)
│   └── requirements.txt
├── frontend/
│   ├── src/App.jsx       # kokpit: wykres (recharts) + suwak ±X%
│   ├── src/index.css
│   └── vite.config.js    # proxy /api -> :8000
├── README.md
└── RAPORT.md             # uzasadnienie stosu i decyzji projektowych
```
