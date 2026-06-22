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

## Uruchomienie na Windows

Kroki są takie same jak na macOS — różni się instalacja wymagań i aktywacja `venv`.

### Wymagania wstępne

Zainstaluj Python 3.10+ i Node 18+ (np. z [python.org](https://www.python.org/downloads/)
i [nodejs.org](https://nodejs.org), albo przez menedżer pakietów):

```powershell
winget install Python.Python.3.12 OpenJS.NodeJS.LTS Git.Git
```

> Przy instalacji Pythona zaznacz **„Add python.exe to PATH"**.

### Backend — terminal nr 1 (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # PowerShell  (w cmd.exe: .\.venv\Scripts\activate.bat)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> Jeśli PowerShell blokuje skrypt aktywacji (`running scripts is disabled`), uruchom raz:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

### Frontend — terminal nr 2

```powershell
cd frontend
npm install
npm run dev
```

UI: <http://localhost:5173>. Sprawdzenie zajętego portu:
`netstat -ano | findstr :8000` (PID w ostatniej kolumnie, ubicie: `taskkill /PID <pid> /F`).

---

## Uruchomienie na Linux

Identyczne jak na macOS (ta sama aktywacja `venv`); różni się tylko instalacja wymagań.

### Wymagania wstępne (Debian/Ubuntu)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip nodejs npm git
```

> Na Fedorze: `sudo dnf install python3 python3-pip nodejs npm git`.
> Jeśli w repo jest stary Node, użyj [nodesource](https://github.com/nodesource/distributions) lub `nvm`.

### Backend — terminal nr 1

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend — terminal nr 2

```bash
cd frontend
npm install
npm run dev
```

UI: <http://localhost:5173>. Sprawdzenie zajętego portu: `ss -ltnp | grep :8000`.

---

## Różnice między systemami (skrót)

| Krok | macOS / Linux | Windows |
|------|---------------|---------|
| Utworzenie venv | `python3 -m venv .venv` | `python -m venv .venv` |
| Aktywacja venv | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |
| Instalacja wymagań | `brew` / `apt` / `dnf` | `winget` / instalatory |
| Sprawdzenie portu | `lsof -nP -i:8000` / `ss -ltnp` | `netstat -ano \| findstr :8000` |

Po aktywacji `venv` reszta poleceń (`pip install -r requirements.txt`,
`uvicorn ...`, `npm install`, `npm run dev`) jest **identyczna na wszystkich systemach**.

---

## Restart serwerów

### Zatrzymanie

Jeśli serwery działają w oknach terminala — naciśnij `Ctrl+C` w każdym z nich.

Jeśli działają w tle (lub nie wiadomo gdzie), zatrzymaj je po porcie:

```bash
# macOS / Linux
kill $(lsof -t -i:8000)      # backend
kill $(lsof -t -i:5173)      # frontend
# albo zbiorczo po nazwie procesu:
pkill -f "uvicorn main:app"
pkill -f vite
```

```powershell
# Windows (PowerShell) — PID z ostatniej kolumny, potem ubicie
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### Ponowne uruchomienie

```bash
# Terminal 1 — backend
cd backend
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Sprawdzenie, że wstały: `curl http://127.0.0.1:8000/api/health` (→ `{"status":"ok"}`)
oraz otwarcie UI na <http://localhost:5173>.

> Flaga `--reload` w uvicornie sama przeładowuje backend po zmianie kodu,
> a Vite ma HMR dla frontendu — pełny restart potrzebny jest rzadko
> (np. po zmianie zależności lub zajętym porcie).

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
