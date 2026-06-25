"""
Testy jednostkowe backendu kokpitu walutowego.

Uruchomienie:
    cd backend
    pytest test_main.py -v
"""
from __future__ import annotations

import pytest
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

import main as m
from main import app, revalue_portfolio, get_rates_for_date, _rates_cache

client = TestClient(app)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    """Czyści cache kursów NBP przed każdym testem (izolacja stanu globalnego)."""
    _rates_cache.clear()
    yield
    _rates_cache.clear()


# ── Dane pomocnicze ────────────────────────────────────────────────────────

ACCOUNTS_MIX = [
    {"id": "A1", "name": "EUR", "currency": "EUR", "balance": 100_000},
    {"id": "A2", "name": "USD", "currency": "USD", "balance": 50_000},
    {"id": "A3", "name": "PLN", "currency": "PLN", "balance": 200_000},
]

SERIES_2 = [
    {"date": "2026-01-02", "rates": {"PLN": 1.0, "EUR": 4.00, "USD": 3.50}},
    {"date": "2026-01-05", "rates": {"PLN": 1.0, "EUR": 4.20, "USD": 3.60}},
]

NBP_RAW = [
    {
        "effectiveDate": "2026-01-02",
        "rates": [
            {"code": "EUR", "mid": 4.2680},
            {"code": "USD", "mid": 3.9420},
            {"code": "CHF", "mid": 4.5000},  # spoza SUPPORTED
        ],
    }
]

MOCK_SERIES = [
    {"date": "2026-06-24", "rates": {"PLN": 1.0, "EUR": 4.2500, "USD": 3.9000}},
    {"date": "2026-06-25", "rates": {"PLN": 1.0, "EUR": 4.2600, "USD": 3.9100}},
]


# ── revalue_portfolio ──────────────────────────────────────────────────────

class TestRevaluePortfolio:

    def test_adjust_zero_exact_calculation(self):
        """adjust=0 → wartość = suma(saldo × kurs NBP)."""
        result = revalue_portfolio(ACCOUNTS_MIX, [SERIES_2[0]], 0.0)
        # 100 000×4.00 + 50 000×3.50 + 200 000×1.0 = 775 000
        assert result[0]["value"] == pytest.approx(775_000.0)

    def test_pln_unaffected_by_adjust(self):
        """Saldo PLN nie zmienia się bez względu na wartość suwaka."""
        pln_only = [{"id": "X", "currency": "PLN", "balance": 500_000}]
        v0  = revalue_portfolio(pln_only, [SERIES_2[0]], 0.0)[0]["value"]
        v10 = revalue_portfolio(pln_only, [SERIES_2[0]], 10.0)[0]["value"]
        assert v0 == v10 == 500_000.0

    def test_positive_adjust_scales_fx(self):
        """adjust=+10% → wartość konta EUR skaluje się przez 1.1."""
        eur = [{"id": "X", "currency": "EUR", "balance": 100_000}]
        v0  = revalue_portfolio(eur, [SERIES_2[0]], 0.0)[0]["value"]
        v10 = revalue_portfolio(eur, [SERIES_2[0]], 10.0)[0]["value"]
        assert v10 == pytest.approx(v0 * 1.1)

    def test_negative_adjust_scales_fx(self):
        """adjust=-5% → wartość konta EUR skaluje się przez 0.95."""
        eur = [{"id": "X", "currency": "EUR", "balance": 100_000}]
        v0    = revalue_portfolio(eur, [SERIES_2[0]], 0.0)[0]["value"]
        v_neg = revalue_portfolio(eur, [SERIES_2[0]], -5.0)[0]["value"]
        assert v_neg == pytest.approx(v0 * 0.95)

    def test_adjust_boundary_plus_50(self):
        """Krawędź zakresu suwaka: adjust=+50%."""
        eur = [{"id": "X", "currency": "EUR", "balance": 100_000}]
        result = revalue_portfolio(eur, [SERIES_2[0]], 50.0)
        assert result[0]["value"] == pytest.approx(100_000 * 4.0 * 1.5)

    def test_adjust_boundary_minus_50(self):
        """Krawędź zakresu suwaka: adjust=-50%."""
        eur = [{"id": "X", "currency": "EUR", "balance": 100_000}]
        result = revalue_portfolio(eur, [SERIES_2[0]], -50.0)
        assert result[0]["value"] == pytest.approx(100_000 * 4.0 * 0.5)

    def test_empty_series_returns_empty_list(self):
        assert revalue_portfolio(ACCOUNTS_MIX, [], 0.0) == []

    def test_empty_accounts_returns_zero_value(self):
        result = revalue_portfolio([], [SERIES_2[0]], 0.0)
        assert result[0]["value"] == 0.0

    def test_missing_currency_rate_skips_account(self):
        """Brak kursu dla waluty konta w danym dniu → konto pomijane."""
        accounts = [
            {"id": "A", "currency": "EUR", "balance": 100_000},
            {"id": "B", "currency": "GBP", "balance": 50_000},  # brak GBP w rates
        ]
        series = [{"date": "2026-01-02", "rates": {"PLN": 1.0, "EUR": 4.0}}]
        result = revalue_portfolio(accounts, series, 0.0)
        assert result[0]["value"] == pytest.approx(400_000.0)

    def test_breakdown_sums_accounts_per_currency(self):
        """Breakdown akumuluje wartość wszystkich kont tej samej waluty."""
        two_eur = [
            {"id": "A", "currency": "EUR", "balance": 60_000},
            {"id": "B", "currency": "EUR", "balance": 40_000},
        ]
        result = revalue_portfolio(two_eur, [SERIES_2[0]], 0.0)
        assert result[0]["breakdown"]["EUR"] == pytest.approx(400_000.0)

    def test_rates_field_contains_original_nbp_rates(self):
        """Pole 'rates' w wyniku to realne kursy NBP (bez korekty)."""
        result = revalue_portfolio(ACCOUNTS_MIX, [SERIES_2[0]], 10.0)
        assert result[0]["rates"]["EUR"] == 4.0

    def test_multiple_days_one_point_per_day(self):
        """Dla serii dwudniowej zwracane są dokładnie dwa punkty."""
        result = revalue_portfolio(ACCOUNTS_MIX, SERIES_2, 0.0)
        assert len(result) == 2
        assert [p["date"] for p in result] == ["2026-01-02", "2026-01-05"]


# ── get_rates_for_date ─────────────────────────────────────────────────────

WINDOW = [
    {"date": "2026-01-02", "rates": {"PLN": 1.0, "EUR": 4.10}},
    {"date": "2026-01-05", "rates": {"PLN": 1.0, "EUR": 4.20}},
    {"date": "2026-01-06", "rates": {"PLN": 1.0, "EUR": 4.25}},
]


class TestGetRatesForDate:

    def test_exact_date_is_used(self):
        """Notowanie z dokładną datą docelową jest wybierane."""
        with patch.object(m, "fetch_nbp_rates", return_value=WINDOW):
            d, rates = get_rates_for_date(date(2026, 1, 5))
        assert d == "2026-01-05"
        assert rates["EUR"] == pytest.approx(4.20)

    def test_weekend_uses_preceding_rate(self):
        """Weekend (sobota) → ostatnie dostępne notowanie przed tą datą."""
        with patch.object(m, "fetch_nbp_rates", return_value=WINDOW):
            # 3 stycznia 2026 to sobota → powinien zwrócić 2026-01-02
            d, _ = get_rates_for_date(date(2026, 1, 3))
        assert d == "2026-01-02"

    def test_date_before_window_uses_first_available(self):
        """Gdy brak notowań przed datą → pierwsze dostępne późniejsze."""
        future_only = [{"date": "2026-06-01", "rates": {"PLN": 1.0, "EUR": 4.30}}]
        with patch.object(m, "fetch_nbp_rates", return_value=future_only):
            d, _ = get_rates_for_date(date(2026, 1, 1))
        assert d == "2026-06-01"

    def test_empty_series_raises_404(self):
        """Pusta seria kursów → HTTPException 404."""
        with patch.object(m, "fetch_nbp_rates", return_value=[]):
            with pytest.raises(HTTPException) as exc:
                get_rates_for_date(date(2026, 1, 2))
        assert exc.value.status_code == 404


# ── fetch_nbp_rates (warstwa HTTP) ────────────────────────────────────────

class TestFetchNbpRates:

    def test_parses_nbp_response_correctly(self, httpx_mock):
        httpx_mock.add_response(json=NBP_RAW)
        result = m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 2))
        assert result[0]["date"] == "2026-01-02"
        assert result[0]["rates"]["EUR"] == pytest.approx(4.2680)
        assert result[0]["rates"]["USD"] == pytest.approx(3.9420)
        assert result[0]["rates"]["PLN"] == 1.0

    def test_unsupported_currencies_excluded(self, httpx_mock):
        """CHF nie jest w SUPPORTED → nie trafia do rates."""
        httpx_mock.add_response(json=NBP_RAW)
        result = m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 2))
        assert "CHF" not in result[0]["rates"]

    def test_nbp_404_raises_http_404(self, httpx_mock):
        """Odpowiedź 404 z NBP → HTTPException 404."""
        httpx_mock.add_response(status_code=404)
        with pytest.raises(HTTPException) as exc:
            m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 2))
        assert exc.value.status_code == 404

    def test_nbp_500_raises_http_502(self, httpx_mock):
        """Odpowiedź 5xx z NBP → HTTPException 502."""
        httpx_mock.add_response(status_code=500)
        with pytest.raises(HTTPException) as exc:
            m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 2))
        assert exc.value.status_code == 502

    def test_result_sorted_ascending_by_date(self, httpx_mock):
        """Wynik jest zawsze posortowany po dacie rosnąco."""
        httpx_mock.add_response(json=[
            {"effectiveDate": "2026-01-05", "rates": [{"code": "EUR", "mid": 4.3}]},
            {"effectiveDate": "2026-01-02", "rates": [{"code": "EUR", "mid": 4.2}]},
        ])
        result = m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 5))
        assert result[0]["date"] < result[1]["date"]

    def test_second_call_hits_cache_not_http(self, httpx_mock):
        """Drugie wywołanie z tym samym zakresem dat nie wysyła żądania HTTP."""
        httpx_mock.add_response(json=NBP_RAW)
        m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 2))
        m.fetch_nbp_rates(date(2026, 1, 2), date(2026, 1, 2))  # powinno trafić w cache
        assert len(httpx_mock.get_requests()) == 1


# ── API endpoints ──────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_returns_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestAccountsEndpoint:

    def test_returns_list(self):
        r = client.get("/api/accounts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_each_account_has_required_fields(self):
        for acc in client.get("/api/accounts").json():
            assert {"id", "name", "currency", "balance"} <= acc.keys()


class TestPortfolioEndpoint:

    def test_returns_200_with_valid_params(self):
        with patch.object(m, "fetch_nbp_rates", return_value=MOCK_SERIES):
            r = client.get("/api/portfolio?days=30&adjust=0")
        assert r.status_code == 200

    def test_response_has_required_keys(self):
        with patch.object(m, "fetch_nbp_rates", return_value=MOCK_SERIES):
            body = client.get("/api/portfolio").json()
        assert {"points", "summary", "factor", "currency", "rates"} <= body.keys()

    def test_currency_is_pln(self):
        with patch.object(m, "fetch_nbp_rates", return_value=MOCK_SERIES):
            body = client.get("/api/portfolio").json()
        assert body["currency"] == "PLN"

    def test_factor_matches_positive_adjust(self):
        with patch.object(m, "fetch_nbp_rates", return_value=MOCK_SERIES):
            body = client.get("/api/portfolio?adjust=10").json()
        assert body["factor"] == pytest.approx(1.1)

    def test_factor_matches_negative_adjust(self):
        with patch.object(m, "fetch_nbp_rates", return_value=MOCK_SERIES):
            body = client.get("/api/portfolio?adjust=-20").json()
        assert body["factor"] == pytest.approx(0.8)

    def test_summary_has_all_required_fields(self):
        with patch.object(m, "fetch_nbp_rates", return_value=MOCK_SERIES):
            s = client.get("/api/portfolio").json()["summary"]
        assert {"first_date", "last_date", "first_value", "last_value",
                "change_abs", "change_pct", "min_value", "max_value"} <= s.keys()

    def test_days_below_minimum_returns_422(self):
        assert client.get("/api/portfolio?days=4").status_code == 422

    def test_days_above_maximum_returns_422(self):
        assert client.get("/api/portfolio?days=91").status_code == 422

    def test_adjust_above_maximum_returns_422(self):
        assert client.get("/api/portfolio?adjust=51").status_code == 422

    def test_adjust_below_minimum_returns_422(self):
        assert client.get("/api/portfolio?adjust=-51").status_code == 422

    def test_nbp_error_propagates_to_client(self):
        with patch.object(m, "fetch_nbp_rates",
                          side_effect=HTTPException(status_code=404, detail="brak danych")):
            r = client.get("/api/portfolio?days=10")
        assert r.status_code == 404


class TestBaselineEndpoint:

    def test_returns_200(self):
        with patch.object(m, "get_rates_for_date",
                          return_value=("2026-01-02", {"PLN": 1.0, "EUR": 4.2680, "USD": 3.9420})):
            r = client.get("/api/baseline")
        assert r.status_code == 200

    def test_response_structure(self):
        with patch.object(m, "get_rates_for_date",
                          return_value=("2026-01-02", {"PLN": 1.0, "EUR": 4.2680, "USD": 3.9420})):
            body = client.get("/api/baseline").json()
        assert {"baseline_date", "rate_date", "currency", "total", "accounts"} <= body.keys()
        assert body["currency"] == "PLN"
        assert body["total"] > 0

    def test_baseline_date_is_january_first(self):
        """Endpoint zawsze odpytuje o kurs z 1 stycznia bieżącego roku."""
        with patch.object(m, "get_rates_for_date",
                          return_value=("2026-01-02", {"PLN": 1.0, "EUR": 4.2680, "USD": 3.9420})) as mock_fn:
            client.get("/api/baseline")
        called_with = mock_fn.call_args[0][0]
        assert called_with.month == 1 and called_with.day == 1
