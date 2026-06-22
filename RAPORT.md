# Raport — Kokpit rewaluacji portfela walutowego

## 1. Cel biznesowy

Aplikacja przeszacowuje (rewaluuje) portfel złożony z 3–5 syntetycznych kont
walutowych (EUR/USD/PLN) do waluty bazowej PLN, korzystając z dziennych
kursów średnich NBP (tabela A). Użytkownik widzi, jak wartość całego portfela
zmieniała się w czasie, oraz może zasymulować scenariusz zmiany kursów
(„co, jeśli złoty osłabi się / umocni o X%").

## 2. Wybór stosu technologicznego (uzasadnienie)

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

Zgodnie z wymaganiem dane trzymane są:
- **konta** — w pliku `backend/accounts.json` (czytelne, łatwe do edycji),
- **kursy NBP** — w **cache w pamięci** procesu (TTL 30 min), co ogranicza
  liczbę zapytań do NBP i przyspiesza ruch suwaka.

## 3. Architektura i przepływ danych

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

## 4. Realizacja wymagań panelu

| Wymaganie | Realizacja |
|-----------|-----------|
| Min. 1 wizualizacja | `LineChart` (Recharts) — wartość portfela w czasie, z linią odniesienia „start" |
| Min. 1 element interaktywny | **Suwak „kurs ±X%"** (zakres −50%…+50%) + dodatkowo selektor okresu (10–90 dni) |
| Przeliczenie po stronie backendu | Suwak ustawia parametr `adjust`, który jest wysyłany do `/api/portfolio`; **całą rewaluację liczy `revalue_portfolio()` w `main.py`**, frontend tylko renderuje gotowy wynik |

### Dlaczego to jest przeliczenie backendowe, a nie filtr w przeglądarce?

Zmiana suwaka **nie modyfikuje** danych już pobranych w przeglądarce. Zamiast tego
wywołuje nowe zapytanie do API z parametrem `adjust`, a backend od nowa przelicza
każdy punkt serii czasowej (kursy FX mnożone przez `1 + adjust/100`). Frontend
otrzymuje gotowe wartości PLN. Ruch suwaka jest **debounce'owany (250 ms)**, aby
nie zalewać backendu zapytaniami podczas przeciągania.

## 5. Model rewaluacji

- Waluta bazowa: **PLN** (kurs 1.0, niewrażliwa na suwak).
- Konta EUR/USD przeliczane kursem średnim NBP danego dnia.
- Korekta `adjust` symuluje zmianę kursów walutowych i dotyczy **wyłącznie części
  walutowej** (EUR/USD); salda PLN pozostają stałe — co odpowiada realnej naturze
  ryzyka kursowego (gotówka w PLN nie podlega rewaluacji).
- NBP publikuje kursy tylko w dni robocze; zakres dat pobierany jest z zapasem
  (`days + 5`), a następnie obcinany do żądanej liczby notowań.

## 6. Obsługa błędów i przypadki brzegowe

- Brak notowań NBP w zakresie (np. same weekendy) → HTTP 404 z czytelnym komunikatem,
  wyświetlanym w panelu wykresu.
- Problem z połączeniem do NBP → HTTP 502.
- Walidacja zakresów `days` (5–90) i `adjust` (−50…+50) na poziomie FastAPI.
- Cache TTL 30 min ogranicza obciążenie NBP i przyspiesza interakcję suwaka.

## 7. Weryfikacja działania

Przykładowe wyniki (20 ostatnich notowań):

| Scenariusz | Wartość portfela (ostatni dzień) |
|------------|----------------------------------|
| `adjust = 0%`   | ~1 543 429 PLN |
| `adjust = +10%` | ~1 662 772 PLN |
| `adjust = −5%`  | ~1 483 758 PLN |

Różnice wynikają wyłącznie ze zmiany części walutowej (saldo PLN = 350 000 stałe),
co potwierdza poprawność modelu i fakt, że przeliczenie odbywa się na backendzie.

## 8. Możliwe rozszerzenia

- Rozbicie wartości portfela na waluty na wykresie (stacked area).
- Dodatkowy suwak osobno dla EUR i USD.
- Eksport wyników do CSV.
- Trwała persystencja (np. SQLite) zamiast pliku JSON.
