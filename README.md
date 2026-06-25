# Kokpit rewaluacji portfela walutowego

Aplikacja webowa przeszacowująca syntetyczne konta walutowe (EUR/USD/PLN) do PLN
po dziennych kursach NBP (tabela A, `api.nbp.pl`).

**Panel:** wykres liniowy wartości portfela w czasie + suwak „kurs ±X%", który
przelicza wartość portfela **po stronie backendu** (a nie tylko filtruje w przeglądarce).

> Projekt: mBank / Wojciech Sitek — zadanie 1.

---

## Live symulator (demo offline)

**https://claude.ai/code/artifact/9ad90f68-bbd0-40ce-99b0-9345c3f6d1a2**

Standalone HTML — działa bez backendu, bez instalacji środowiska. Zawiera:

- **Wykres liniowy** wartości portfela w czasie (10 / 20 / 30 / 60 / 90 dni)
- **Suwak ±50%** korygujący kursy walut — z debouncingiem i wskaźnikiem „przeliczanie…"
- **Tooltip** przy najeździe na wykres — pionowa linia + dot, aktualizuje tabelę kursów
- **Tabela kursów NBP vs po korekcie** z różnicą nominalną (zielona / czerwona)
- **Tabela kont** z wartościami wyjściowymi (EUR, USD, PLN) i sumą na 2026-01-02
- Infotipy (ⓘ) z pełnymi opisami jak w aplikacji

Dane: syntetyczne kursy NBP-like (EUR ≈ 4,27 PLN, USD ≈ 3,94 PLN, deterministyczny random walk).

---

## Stos technologiczny

| Warstwa   | Technologia                      |
|-----------|----------------------------------|
| Backend   | Python 3.10 + FastAPI + httpx    |
| Frontend  | React 18 + Vite + Recharts       |
| Dane      | plik JSON (`backend/accounts.json`) + cache kursów NBP w pamięci |
| Źródło kursów | NBP API, tabela A (`api.nbp.pl`) |

---

## Uruchomienie

Wymagania: Python 3.10+ i Node 18+.

```bash
# Terminal 1 — backend (port 8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend (port 5173)
cd frontend
npm install
npm run dev
```

UI: <http://localhost:5173> · Swagger: <http://localhost:8000/docs>

Dev-server Vite proxuje `/api/*` do backendu na `:8000` — nie trzeba nic dodatkowo konfigurować.

> **VS Code Remote SSH / Tunnels** — w panelu **PORTS** przekaż porty **5173** i **8000**
> na maszynę lokalną, a następnie otwieraj UI przez forwardowany 5173.

Zatrzymanie serwerów działających w tle:

```bash
pkill -f "uvicorn main:app"
pkill -f vite
```

---

## API

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| `GET`  | `/api/health` | Status serwisu |
| `GET`  | `/api/accounts` | Lista syntetycznych kont |
| `GET`  | `/api/baseline` | Wartość portfela wyceniona kursami z 1 stycznia |
| `GET`  | `/api/portfolio?days=30&adjust=0` | Seria czasowa wartości portfela w PLN. `adjust` = korekta kursu w % (suwak); **przeliczenie wykonuje backend** |

```bash
curl "http://127.0.0.1:8000/api/portfolio?days=20&adjust=10"
```

---

## Struktura

```
kokpitwalutowy/
├── backend/
│   ├── main.py           # FastAPI: pobieranie kursów NBP + rewaluacja
│   ├── accounts.json     # 5 syntetycznych kont (EUR/USD/PLN)
│   └── requirements.txt
├── frontend/
│   ├── src/App.jsx       # kokpit: wykres (Recharts) + suwak ±X%
│   ├── src/index.css
│   └── vite.config.js    # proxy /api → :8000
└── README.md
```

---

## Cel biznesowy

Aplikacja przeszacowuje (rewaluuje) portfel złożony z 3–5 syntetycznych kont
walutowych (EUR/USD/PLN) do waluty bazowej PLN, korzystając z dziennych
kursów średnich NBP (tabela A). Użytkownik widzi, jak wartość całego portfela
zmieniała się w czasie, oraz może zasymulować scenariusz zmiany kursów
(„co, jeśli złoty osłabi się / umocni o X%").

---

## Uzasadnienie stosu technologicznego

Zadanie dopuszcza dowolny stos; wybrano **proponowany: FastAPI + React**.

### Backend — FastAPI (Python)

- **Walidacja parametrów out-of-the-box.** Parametry `days` i `adjust` są
  walidowane deklaratywnie (`Query(..., ge=-50, le=50)`), co eliminuje ręczne
  sprawdzanie zakresów i chroni endpoint przeliczeń.
- **Automatyczna dokumentacja.** Swagger UI (`/docs`) dostępny bez dodatkowej
  pracy — ułatwia weryfikację i prezentację API.
- **`httpx` do integracji z NBP.** Prosty, nowoczesny klient HTTP z timeoutami
  i czytelną obsługą błędów (404 = brak notowań w zakresie, 502 = problem z NBP).
- **Lekkość.** Brak ORM/bazy — idealne do zadania bez warstwy persystencji.

### Frontend — React + Vite + Recharts

- **Recharts** to deklaratywna biblioteka wykresów oparta na komponentach React;
  `LineChart` realizuje wymaganą wizualizację minimalnym kodem.
- **Vite** daje szybki dev-server i wbudowane **proxy `/api` → backend**, dzięki
  czemu te same ścieżki względne działają w dev i w produkcji (brak problemów z CORS
  w realnym wdrożeniu za jednym reverse-proxy).

### Brak bazy danych

- **Konta** — w pliku `backend/accounts.json` (czytelne, łatwe do edycji).
- **Kursy NBP** — w **cache w pamięci** procesu (TTL 30 min), co ogranicza
  liczbę zapytań do NBP i przyspiesza ruch suwaka.

---

## Architektura i przepływ danych

```
Przeglądarka (React)                  Backend (FastAPI)                NBP API
─────────────────────                ──────────────────               ────────
suwak ±X% / wybór dni  ──/api/portfolio?days&adjust──▶  fetch tabela A ──▶ api.nbp.pl
                                          │  (cache 30 min w pamięci)
       wykres liniowy  ◀── JSON: seria {date, value} ──┘
                            (rewaluacja policzona na serwerze)
```

1. Frontend wysyła `GET /api/portfolio?days=&adjust=`.
2. Backend pobiera (lub bierze z cache) kursy NBP tabeli A dla zakresu dat.
3. Backend liczy dla każdego dnia wartość portfela w PLN, stosując korektę kursu.
4. Frontend rysuje serię na wykresie i pokazuje podsumowanie.

---

## Realizacja wymagań panelu

| Wymaganie | Realizacja |
|-----------|-----------|
| Min. 1 wizualizacja | `LineChart` (Recharts) — wartość portfela w czasie, z linią odniesienia „start" |
| Min. 1 element interaktywny | **Suwak „kurs ±X%"** (zakres −50%…+50%) + selektor okresu (10–90 dni) |
| Przeliczenie po stronie backendu | Suwak ustawia parametr `adjust` wysyłany do `/api/portfolio`; **całą rewaluację liczy `revalue_portfolio()` w `main.py`**, frontend tylko renderuje gotowy wynik |

Zmiana suwaka **nie modyfikuje** danych już pobranych w przeglądarce — wywołuje nowe
zapytanie do API z parametrem `adjust`, a backend od nowa przelicza każdy punkt serii
czasowej. Ruch suwaka jest **debounce'owany (250 ms)**, aby nie zalewać backendu
zapytaniami podczas przeciągania.

---

## Model rewaluacji

- Waluta bazowa: **PLN** (kurs 1,0 — niewrażliwa na suwak).
- Konta EUR/USD przeliczane kursem średnim NBP danego dnia.
- Korekta `adjust` dotyczy **wyłącznie części walutowej** (EUR/USD); salda PLN pozostają
  stałe — co odpowiada realnej naturze ryzyka kursowego.
- NBP publikuje kursy tylko w dni robocze; zakres dat pobierany jest z zapasem
  (`days + 5`), a następnie obcinany do żądanej liczby notowań.

---

## Korekta kursu a „zmiana w okresie"

To dwa różne pojęcia; aplikacja pokazuje oba.

### Korekta kursu (suwak ±X%)

Hipotetyczny scenariusz **„co, jeśli"**: jak zmieniłaby się wartość portfela, gdyby
wszystkie kursy walut były o X% wyższe/niższe niż faktycznie opublikował NBP?

```python
factor = 1.0 + adjust_pct / 100.0          # +10% → 1.10, −5% → 0.95
rate = base_rate if cur == "PLN" else base_rate * factor
```

Efekt na wykresie: **przesunięcie całej krzywej** w górę/dół (wszystkie dni skalowane
tym samym współczynnikiem).

| adjust | kurs EUR | część EUR | + PLN | wartość portfela |
|--------|----------|-----------|-------|------------------|
| `0%`   | 4,20     | 420 000   | 350 000 | 770 000 |
| `+10%` | 4,62     | 462 000   | 350 000 | 812 000 |
| `−5%`  | 3,99     | 399 000   | 350 000 | 749 000 |

### Zmiana w okresie

Różnica wartości portfela między **pierwszym a ostatnim dniem** wybranego zakresu —
efekt tego, jak **realne kursy NBP poruszały się w czasie** (nie efekt suwaka).
Na wykresie zaznaczona liniami odniesienia „start" i „koniec".

### Jak suwak wpływa na zmianę w okresie?

Ponieważ stała część PLN skraca się w odejmowaniu, suwak skaluje *bezwzględną* zmianę
przez `factor`:

| adjust | zmiana bezwzględna | zmiana % |
|--------|--------------------|----------|
| `0%`   | +10 000            | +1,30%   |
| `+10%` | +11 000 (×1,1)     | +1,35%   |

**Podsumowanie:**
- **Suwak ±X%** = hipotetyczny scenariusz na *poziom* kursów (przesuwa całą krzywą).
- **Zmiana w okresie** = faktyczny ruch kursów NBP *w czasie* (nachylenie krzywej).

---

## Obsługa błędów i przypadki brzegowe

- Brak notowań NBP w zakresie (np. same weekendy) → HTTP 404 z czytelnym komunikatem.
- Problem z połączeniem do NBP → HTTP 502.
- Walidacja zakresów `days` (5–90) i `adjust` (−50…+50) na poziomie FastAPI.
- Cache TTL 30 min ogranicza obciążenie NBP i przyspiesza interakcję suwaka.

---

## Weryfikacja działania

Przykładowe wyniki (20 ostatnich notowań):

| Scenariusz | Wartość portfela (ostatni dzień) |
|------------|----------------------------------|
| `adjust = 0%`   | ~1 543 429 PLN |
| `adjust = +10%` | ~1 662 772 PLN |
| `adjust = −5%`  | ~1 483 758 PLN |

Różnice wynikają wyłącznie ze zmiany części walutowej (saldo PLN = 350 000 stałe),
co potwierdza poprawność modelu i fakt, że przeliczenie odbywa się na backendzie.

---

## Możliwe rozszerzenia

- Rozbicie wartości portfela na waluty na wykresie (stacked area).
- Dodatkowy suwak osobno dla EUR i USD.
- Eksport wyników do CSV.
- Trwała persystencja (np. SQLite) zamiast pliku JSON.
