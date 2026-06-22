"""
Kokpit rewaluacji portfela walutowego — backend FastAPI.

Przeszacowuje syntetyczne konta (EUR/USD/PLN) do PLN po dziennych kursach
NBP (tabela A, api.nbp.pl). Dane kont trzymane w pliku JSON, kursy NBP
cache'owane w pamięci. Korekta kursu (suwak "±X%") liczona jest TUTAJ,
po stronie backendu — frontend wysyła parametr `adjust`, a serwer od nowa
przelicza całą serię czasową wartości portfela.
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"

NBP_BASE = "https://api.nbp.pl/api/exchangerates/tables/A"
# Waluty obsługiwane w portfelu (PLN jest walutą bazową — kurs 1.0).
SUPPORTED = {"EUR", "USD", "PLN"}

app = FastAPI(title="Kokpit rewaluacji portfela walutowego", version="1.0.0")

# Frontend (Vite) działa na innym porcie, więc otwieramy CORS dla dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prosty cache w pamięci: klucz = (start, end) -> (timestamp, dane)
_rates_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}
_CACHE_TTL = 60 * 30  # 30 minut


def load_accounts() -> list[dict]:
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def fetch_nbp_rates(start: date, end: date) -> list[dict]:
    """
    Pobiera tabelę A NBP dla zakresu dat. Zwraca listę:
        [{ "date": "YYYY-MM-DD", "rates": {"EUR": 4.24, "USD": 3.68, "PLN": 1.0} }, ...]
    Cache w pamięci (TTL 30 min). NBP zwraca tylko dni robocze.
    """
    cache_key = (start.isoformat(), end.isoformat())
    now = time.time()
    cached = _rates_cache.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    url = f"{NBP_BASE}/{start.isoformat()}/{end.isoformat()}?format=json"
    try:
        resp = httpx.get(url, timeout=15.0, headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Błąd połączenia z NBP: {exc}") from exc

    if resp.status_code == 404:
        # Brak danych w zakresie (np. same weekendy/święta).
        raise HTTPException(status_code=404, detail="NBP nie ma danych w tym zakresie dat.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"NBP zwróciło status {resp.status_code}.")

    series: list[dict] = []
    for table in resp.json():
        day_rates = {"PLN": 1.0}  # waluta bazowa
        for r in table["rates"]:
            if r["code"] in SUPPORTED:
                day_rates[r["code"]] = r["mid"]
        series.append({"date": table["effectiveDate"], "rates": day_rates})

    series.sort(key=lambda x: x["date"])
    _rates_cache[cache_key] = (now, series)
    return series


def revalue_portfolio(accounts: list[dict], series: list[dict], adjust_pct: float) -> list[dict]:
    """
    Przelicza wartość portfela do PLN dla każdego dnia z serii kursów.
    `adjust_pct` to korekta kursów walutowych w procentach (suwak ±X%).
    Kursy FX mnożone są przez (1 + adjust_pct/100); saldo PLN bez zmian.
    """
    factor = 1.0 + adjust_pct / 100.0
    out: list[dict] = []
    for day in series:
        rates = day["rates"]
        total = 0.0
        breakdown: dict[str, float] = {}
        for acc in accounts:
            cur = acc["currency"]
            base_rate = rates.get(cur)
            if base_rate is None:
                continue  # brak kursu danego dnia dla tej waluty
            # PLN nie podlega korekcie kursu (to waluta bazowa, kurs = 1.0).
            rate = base_rate if cur == "PLN" else base_rate * factor
            value = acc["balance"] * rate
            total += value
            breakdown[cur] = round(breakdown.get(cur, 0.0) + value, 2)
        out.append({
            "date": day["date"],
            "value": round(total, 2),
            "breakdown": breakdown,
        })
    return out


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/accounts")
def get_accounts():
    """Lista syntetycznych kont w portfelu."""
    return load_accounts()


@app.get("/api/portfolio")
def get_portfolio(
    days: int = Query(30, ge=5, le=90, description="Ile dni wstecz pobrać kursy NBP"),
    adjust: float = Query(0.0, ge=-50.0, le=50.0, description="Korekta kursu w % (suwak ±X%)"),
):
    """
    Główny endpoint kokpitu. Zwraca serię czasową wartości portfela w PLN
    po kursach NBP, z uwzględnieniem korekty kursu `adjust` (liczonej tutaj).
    """
    accounts = load_accounts()
    end = date.today()
    # Bierzemy zapas dni, bo NBP pomija weekendy/święta.
    start = end - timedelta(days=days + 5)
    series = fetch_nbp_rates(start, end)

    # Ograniczamy do żądanej liczby ostatnich notowań.
    series = series[-days:] if len(series) > days else series

    revalued = revalue_portfolio(accounts, series, adjust)
    if not revalued:
        raise HTTPException(status_code=404, detail="Brak danych do przeszacowania.")

    base = revalued[0]["value"]
    last = revalued[-1]["value"]
    return {
        "adjust": adjust,
        "currency": "PLN",
        "points": revalued,
        "summary": {
            "first_date": revalued[0]["date"],
            "last_date": revalued[-1]["date"],
            "first_value": base,
            "last_value": last,
            "change_abs": round(last - base, 2),
            "change_pct": round((last - base) / base * 100, 2) if base else 0.0,
            "min_value": min(p["value"] for p in revalued),
            "max_value": max(p["value"] for p in revalued),
        },
    }
