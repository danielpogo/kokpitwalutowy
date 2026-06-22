import { useEffect, useMemo, useRef, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

const PLN = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: "PLN",
  maximumFractionDigits: 0,
});
const PLN2 = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: "PLN",
  maximumFractionDigits: 2,
});
const RATE = new Intl.NumberFormat("pl-PL", {
  minimumFractionDigits: 4,
  maximumFractionDigits: 6,
});

// Mała ikona "ⓘ" z natywnym tooltipem (atrybut title) — bez dodatkowych zależności.
function InfoTip({ text }) {
  return (
    <span className="infotip" title={text} aria-label={text}>
      ⓘ
    </span>
  );
}

function Tip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      style={{
        background: "#0f172a",
        border: "1px solid #334155",
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 13,
      }}
    >
      <div style={{ color: "#94a3b8" }}>{label}</div>
      <div style={{ color: "#38bdf8", fontWeight: 600 }}>
        {PLN2.format(payload[0].value)}
      </div>
    </div>
  );
}

export default function App() {
  const [days, setDays] = useState(30);
  const [adjust, setAdjust] = useState(0); // suwak kurs ±X%
  const [data, setData] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const debounceRef = useRef(null);

  // Lista kont (raz przy starcie).
  useEffect(() => {
    fetch("/api/accounts")
      .then((r) => r.json())
      .then(setAccounts)
      .catch(() => {});
  }, []);

  // Pobranie/przeliczenie portfela. Suwak `adjust` jest debounce'owany,
  // a samo przeliczenie wykonuje BACKEND (parametr ?adjust=).
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(
      () => {
        setLoading(true);
        setError(null);
        fetch(`/api/portfolio?days=${days}&adjust=${adjust}`)
          .then(async (r) => {
            if (!r.ok) {
              const body = await r.json().catch(() => ({}));
              throw new Error(body.detail || `Błąd ${r.status}`);
            }
            return r.json();
          })
          .then((d) => setData(d))
          .catch((e) => setError(e.message))
          .finally(() => setLoading(false));
      },
      adjust === 0 ? 0 : 250
    );
    return () => clearTimeout(debounceRef.current);
  }, [days, adjust]);

  const summary = data?.summary;
  const change = summary?.change_abs ?? 0;
  const changeClass = change >= 0 ? "green" : "red";

  const chartData = useMemo(
    () => (data?.points ?? []).map((p) => ({ date: p.date.slice(5), value: p.value })),
    [data]
  );
  const baseValue = data?.points?.[0]?.value;
  const lastValue = data?.points?.[data.points.length - 1]?.value;
  const rates = data?.rates; // { date, items: [{code, nbp, adjusted, diff}] }

  return (
    <div className="app">
      <h1>Kokpit rewaluacji portfela walutowego</h1>
      <p className="subtitle">
        Przeszacowanie syntetycznych kont (EUR/USD/PLN) do PLN po dziennych kursach
        NBP (tabela A). Korekta kursu liczona po stronie backendu.
      </p>

      {/* Karty podsumowania */}
      <div className="cards">
        <div className="card">
          <div className="label">Wartość portfela (ostatni dzień)</div>
          <div className="value">{summary ? PLN.format(summary.last_value) : "—"}</div>
        </div>
        <div className="card">
          <div className="label">
            Zmiana w okresie{" "}
            <InfoTip text="Różnica wartości portfela między pierwszym a ostatnim dniem wybranego okresu. Pokazuje, jak realne kursy NBP poruszały się w czasie (to NIE efekt suwaka). Zielona = wzrost, czerwona = spadek wartości w PLN." />
          </div>
          <div className={`value ${changeClass}`}>
            {summary
              ? `${change >= 0 ? "+" : ""}${PLN.format(change)} (${summary.change_pct}%)`
              : "—"}
          </div>
        </div>
        <div className="card">
          <div className="label">Zakres dat</div>
          <div className="value" style={{ fontSize: "1.05rem" }}>
            {summary ? `${summary.first_date} → ${summary.last_date}` : "—"}
          </div>
        </div>
        <div className="card">
          <div className="label">
            Korekta kursu{" "}
            <InfoTip text="Hipotetyczny scenariusz „co, jeśli”: wszystkie kursy walut (EUR/USD) mnożone przez (1 ± X%) we wszystkich dniach naraz. Saldo PLN bez zmian. Przeliczenie wykonuje backend." />
          </div>
          <div className="value" style={{ color: "var(--accent)" }}>
            {adjust > 0 ? "+" : ""}
            {adjust}%
          </div>
        </div>
      </div>

      {/* Panel sterowania */}
      <div className="panel">
        <div className="controls">
          <div className="control">
            <label>
              <span>Suwak: kurs walut ±X% (przeliczany na backendzie)</span>
              <span className="slider-value">
                {adjust > 0 ? "+" : ""}
                {adjust}%
              </span>
            </label>
            <input
              type="range"
              min={-50}
              max={50}
              step={1}
              value={adjust}
              onChange={(e) => setAdjust(Number(e.target.value))}
            />
            <div className="hint">
              Symuluje umocnienie/osłabienie złotego. Salda PLN pozostają bez zmian —
              przeliczana jest tylko część walutowa (EUR/USD).
            </div>
          </div>

          <div className="control" style={{ flex: "0 0 auto" }}>
            <label htmlFor="days">
              <span>Okres (dni notowań)</span>
            </label>
            <select
              id="days"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={10}>10 dni</option>
              <option value={20}>20 dni</option>
              <option value={30}>30 dni</option>
              <option value={60}>60 dni</option>
              <option value={90}>90 dni</option>
            </select>
            {loading && <span className="loading-dot">● przeliczanie…</span>}
          </div>
        </div>
      </div>

      {/* Wykres liniowy */}
      <div className="panel">
        <h3 style={{ marginTop: 0, marginBottom: 4 }}>Wartość portfela w czasie (PLN)</h3>
        {summary && (
          <p className="chart-caption">
            Zmiana w okresie ({summary.first_date} → {summary.last_date}):{" "}
            <span className={changeClass} style={{ fontWeight: 700 }}>
              {change >= 0 ? "+" : ""}
              {PLN2.format(change)} ({summary.change_pct}%)
            </span>
          </p>
        )}
        {error ? (
          <div className="status error">Błąd: {error}</div>
        ) : !data ? (
          <div className="status">Ładowanie danych z NBP…</div>
        ) : (
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={12}
                  width={80}
                  domain={["auto", "auto"]}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<Tip />} />
                {baseValue != null && (
                  <ReferenceLine
                    y={baseValue}
                    stroke="#64748b"
                    strokeDasharray="4 4"
                    label={{ value: "start", fill: "#64748b", fontSize: 11, position: "insideTopRight" }}
                  />
                )}
                {lastValue != null && (
                  <ReferenceLine
                    y={lastValue}
                    stroke={change >= 0 ? "#34d399" : "#f87171"}
                    strokeDasharray="4 4"
                    label={{
                      value: `koniec ${change >= 0 ? "+" : ""}${summary?.change_pct}%`,
                      fill: change >= 0 ? "#34d399" : "#f87171",
                      fontSize: 11,
                      position: "insideBottomRight",
                    }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#38bdf8"
                  strokeWidth={2.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Kursy NBP vs kurs po korekcie (wartości nominalne) */}
      {rates && rates.items.length > 0 && (
        <div className="panel">
          <h3 style={{ marginTop: 0, marginBottom: 4 }}>
            Kursy NBP a korekta kursu{" "}
            <InfoTip text="Realny średni kurs NBP (tabela A) z ostatniego dnia okresu vs kurs po korekcie ±X% (w wartościach nominalnych). PLN to waluta bazowa (kurs 1,0), nie podlega korekcie." />
          </h3>
          <p className="chart-caption">
            Stan na {rates.date} · korekta {adjust > 0 ? "+" : ""}
            {adjust}% (mnożnik ×{(1 + adjust / 100).toFixed(4)})
          </p>
          <table>
            <thead>
              <tr>
                <th>Waluta</th>
                <th className="num">Kurs NBP (PLN)</th>
                <th className="num">Kurs po korekcie (PLN)</th>
                <th className="num">Różnica nominalna</th>
              </tr>
            </thead>
            <tbody>
              {rates.items.map((r) => {
                const diffClass = r.diff > 0 ? "green" : r.diff < 0 ? "red" : "";
                return (
                  <tr key={r.code}>
                    <td>
                      <span className="badge">{r.code}</span>
                    </td>
                    <td className="num">{RATE.format(r.nbp)}</td>
                    <td className="num">{RATE.format(r.adjusted)}</td>
                    <td className={`num ${diffClass}`}>
                      {r.diff > 0 ? "+" : ""}
                      {RATE.format(r.diff)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Tabela kont */}
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Konta w portfelu</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nazwa</th>
              <th>Waluta</th>
              <th className="num">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td>{a.id}</td>
                <td>{a.name}</td>
                <td>
                  <span className="badge">{a.currency}</span>
                </td>
                <td className="num">
                  {new Intl.NumberFormat("pl-PL", { minimumFractionDigits: 2 }).format(
                    a.balance
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
