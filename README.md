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

## Uruchomienie na macOS (krok po kroku)

### Wymagania wstępne

```bash
python3 --version   # potrzeba 3.10+
node --version      # potrzeba 18+ (zalecane 20+)
```

Jeśli czegoś brakuje, najprościej przez [Homebrew](https://brew.sh):

```bash
brew install python node git
```

### 1. Pobranie kodu

```bash
git clone https://github.com/danielpogo/kokpitwalutowy.git
cd kokpitwalutowy
```

### 2. Backend — terminal nr 1

```bash
cd backend
python3 -m venv .venv          # wirtualne środowisko (izolacja zależności)
source .venv/bin/activate       # aktywacja (macOS/Linux)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Sprawdź: <http://127.0.0.1:8000/api/health> → `{"status":"ok"}`.
Backend pobiera kursy z `api.nbp.pl`, więc wymaga dostępu do internetu.

### 3. Frontend — terminal nr 2

Zostaw backend działający i otwórz **drugie okno/zakładkę terminala**:

```bash
cd kokpitwalutowy/frontend
npm install
npm run dev
```

Otwórz w przeglądarce: **<http://localhost:5173>**

```
Terminal 1: backend  → uvicorn na :8000  (kursy NBP + przeliczenia)
Terminal 2: frontend → vite    na :5173  (UI; proxy /api → :8000)
```

Zatrzymanie: `Ctrl+C` w obu terminalach. Ponowna aktywacja środowiska
backendu później: `source backend/.venv/bin/activate`.

### Najczęstsze problemy na macOS

| Problem | Rozwiązanie |
|---------|-------------|
| `command not found: python3` | `brew install python` |
| Port 8000 lub 5173 zajęty | zmień port, np. `uvicorn main:app --port 8001`, i popraw `target` w `frontend/vite.config.js` |
| Wykres pusty / błąd 404 z NBP | sprawdź internet; NBP publikuje kursy tylko w dni robocze (aplikacja bierze zakres z zapasem) |
| Błędy SSL przy `pip install` | użyj Pythona z Homebrew zamiast systemowego |

> **Ważne — który adres otwierać?**
> Interfejs aplikacji (wykres + suwak) jest na **porcie 5173**. Port **8000 serwuje
> wyłącznie API** (`/api/...`) i **nie ma strony pod `/`** — otwarcie
> `http://127.0.0.1:8000/` w przeglądarce zwróci 404 (to normalne). Backend
> sprawdzaj endpointami, np. `/api/health` lub dokumentacją `/docs`.

### Praca przez VS Code Remote / port forwarding

Jeśli edytujesz kod na zdalnej maszynie przez **VS Code Remote-SSH / Tunnels**, VS Code
automatycznie forwarduje porty na Twój komputer. Typowy objaw problemu: `curl`
pokazuje `request completely sent off` i wisi, a strona się nie ładuje.

- **Przyczyna:** forward portu istnieje, ale serwer (uvicorn/vite) **na zdalnej maszynie
  nie działa** — VS Code przyjmuje połączenie, lecz nie ma czego przekazać → zwis.
- **Rozwiązanie:** uruchom backend i frontend **na maszynie, gdzie jest kod** (tej
  zdalnej), a w VS Code w panelu **PORTS** upewnij się, że **5173** i **8000** są
  forwardowane. UI otwieraj przez forwardowany **5173** (ikona 🌐 w panelu PORTS).
- Sprawdzenie, co faktycznie nasłuchuje na porcie (na zdalnej maszynie):
  ```bash
  lsof -nP -i:8000          # macOS
  ss -ltnp | grep :8000     # Linux
  ```
  W kolumnie procesu powinno być `uvicorn`/`python`. Jeśli widzisz `Code Helper`
  (VS Code) jako `LISTEN`, to tylko forward — realny backend musi działać po stronie zdalnej.

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
