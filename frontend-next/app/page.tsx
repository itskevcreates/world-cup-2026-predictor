"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type TeamElo = { team: string; elo: number };
type Prediction = {
  home: string;
  away: string;
  expected_goals: { home: number; away: number };
  probabilities: { home_win: number; draw: number; away_win: number };
  most_likely_scorelines: { score: string; prob: number }[];
};
type Power = {
  team: string; power: number; attack: number; defense: number;
  momentum: number; schedule_strength: number; tournament_elo: number;
};
type Outlook = {
  team: string;
  advance_pct: number;
  quarter_pct: number;
  semi_pct: number;
  final_pct: number;
  title_pct: number;
};

function tier(pct: number) {
  if (pct >= 10) return { label: "Favorite", color: "#22d3a6" };
  if (pct >= 3) return { label: "Contender", color: "#5b9dff" };
  if (pct > 0) return { label: "Dark horse", color: "#c084fc" };
  return { label: "Outsider", color: "#64748b" };
}

function Bar({ pct, label }: { pct: number; label: string }) {
  return (
    <div className="mt-2">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="tabular-nums">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded bg-[#0e1530] overflow-hidden mt-1">
        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Home() {
  const [teams, setTeams] = useState<TeamElo[]>([]);
  const [home, setHome] = useState("Spain");
  const [away, setAway] = useState("Brazil");
  const [pred, setPred] = useState<Prediction | null>(null);
  const [outlook, setOutlook] = useState<Outlook[]>([]);
  const [powers, setPowers] = useState<Power[]>([]);
  const [loadingSim, setLoadingSim] = useState(false);

  useEffect(() => {
    fetch(`${API}/teams`).then((r) => r.json()).then(setTeams).catch(() => {});
    fetch(`${API}/power`).then((r) => r.json()).then(setPowers).catch(() => {});
  }, []);

  async function predict() {
    const r = await fetch(`${API}/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`);
    setPred(await r.json());
  }

  async function simulate() {
    setLoadingSim(true);
    const r = await fetch(`${API}/simulate?n=10000`);
    const d = await r.json();
    setOutlook((d.outlook as Outlook[]).filter((t) => t.title_pct > 0).slice(0, 20));
    setLoadingSim(false);
  }

  return (
    <main className="max-w-5xl mx-auto px-4 pb-16">
      <header className="text-center py-7">
        <h1 className="text-3xl font-bold">⚽ World Cup 2026 — Prediction Platform</h1>
        <p className="text-muted mt-1">USA · Mexico · Canada — trained ML model + Monte Carlo simulation</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Match predictor */}
        <section className="bg-card border border-[#243056] rounded-2xl p-5">
          <h2 className="font-semibold mb-3">Match Predictor</h2>
          <div className="flex flex-wrap gap-2 items-center">
            <select className="bg-[#0e1530] border border-[#2c3a66] rounded-lg px-3 py-2"
              value={home} onChange={(e) => setHome(e.target.value)}>
              {teams.map((t) => <option key={t.team} value={t.team}>{t.team}</option>)}
            </select>
            <span className="text-muted">vs</span>
            <select className="bg-[#0e1530] border border-[#2c3a66] rounded-lg px-3 py-2"
              value={away} onChange={(e) => setAway(e.target.value)}>
              {teams.map((t) => <option key={t.team} value={t.team}>{t.team}</option>)}
            </select>
            <button onClick={predict}
              className="bg-accent text-[#04231a] font-bold rounded-lg px-4 py-2">Predict</button>
          </div>
          {pred && (
            <div className="mt-4">
              <div className="flex justify-between">
                <b>{pred.home}</b>
                <span className="text-muted text-sm">
                  xG {pred.expected_goals.home} – {pred.expected_goals.away}
                </span>
                <b>{pred.away}</b>
              </div>
              <Bar label={`${pred.home} win`} pct={pred.probabilities.home_win * 100} />
              <Bar label="Draw" pct={pred.probabilities.draw * 100} />
              <Bar label={`${pred.away} win`} pct={pred.probabilities.away_win * 100} />
              <p className="text-muted text-sm mt-2">
                Likely scores: {pred.most_likely_scorelines.map((s) => s.score).join(" · ")}
              </p>
            </div>
          )}
        </section>

        {/* Simulation */}
        <section className="bg-card border border-[#243056] rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Title Outlook</h2>
            {outlook.length > 0 && (
              <span className="text-muted text-xs">10,000 simulations</span>
            )}
          </div>
          <button onClick={simulate} disabled={loadingSim}
            className="bg-accent text-[#04231a] font-bold rounded-lg px-4 py-2 disabled:opacity-60">
            {loadingSim ? "Running 10,000 sims…" : "Run Monte Carlo"}
          </button>

          {outlook.length > 0 && (
            <>
              <div className="flex gap-3 text-xs mt-4 mb-2">
                <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full" style={{ background: "#22d3a6" }} />Favorite</span>
                <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full" style={{ background: "#5b9dff" }} />Contender</span>
                <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full" style={{ background: "#c084fc" }} />Dark horse</span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted text-left text-xs">
                    <th className="py-1 font-medium">Team</th>
                    <th className="font-medium text-right">SF</th>
                    <th className="font-medium text-right">Final</th>
                    <th className="font-medium pl-3">Win</th>
                  </tr>
                </thead>
                <tbody>
                  {outlook.map((o, i) => {
                    const t = tier(o.title_pct);
                    const max = outlook[0].title_pct;
                    return (
                      <tr key={o.team} className="border-t border-[#1d2747]">
                        <td className="py-1.5">
                          <span className="text-muted mr-2 tabular-nums">{i + 1}</span>
                          {o.team}
                          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full"
                            style={{ background: `${t.color}22`, color: t.color }}>{t.label}</span>
                        </td>
                        <td className="text-right tabular-nums text-muted">{o.semi_pct}%</td>
                        <td className="text-right tabular-nums text-muted">{o.final_pct}%</td>
                        <td className="pl-3">
                          <div className="flex items-center gap-2">
                            <div className="h-2 rounded bg-[#0e1530] overflow-hidden flex-1 min-w-[60px]">
                              <div className="h-full rounded" style={{ width: `${(o.title_pct / max) * 100}%`, background: t.color }} />
                            </div>
                            <span className="tabular-nums w-12 text-right font-medium">{o.title_pct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          )}
        </section>
      </div>

      {/* Dynamic power ratings */}
      {powers.length > 0 && (
        <section className="bg-card border border-[#243056] rounded-2xl p-5 mt-4">
          <h2 className="font-semibold mb-1">Dynamic Power Ratings</h2>
          <p className="text-muted text-xs mb-3">
            Tournament-first: 60% current 2026 performance (opponent-adjusted, dominance,
            momentum), 40% prior. Reputation no longer decides the order.
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted text-left text-xs">
                <th className="py-1 font-medium">#</th>
                <th className="font-medium">Team</th>
                <th className="font-medium text-right">Power</th>
                <th className="font-medium text-right">Atk</th>
                <th className="font-medium text-right">Def</th>
                <th className="font-medium text-right">Mom.</th>
                <th className="font-medium text-right">SOS</th>
              </tr>
            </thead>
            <tbody>
              {powers.slice(0, 14).map((p, i) => (
                <tr key={p.team} className="border-t border-[#1d2747]">
                  <td className="py-1.5 text-muted tabular-nums">{i + 1}</td>
                  <td>{p.team}</td>
                  <td className="text-right tabular-nums font-medium">{p.power.toFixed(0)}</td>
                  <td className="text-right tabular-nums text-muted">{p.attack.toFixed(0)}</td>
                  <td className="text-right tabular-nums text-muted">{p.defense.toFixed(0)}</td>
                  <td className="text-right tabular-nums" style={{ color: p.momentum >= 0 ? "#22d3a6" : "#f87171" }}>
                    {p.momentum >= 0 ? "+" : ""}{p.momentum.toFixed(0)}
                  </td>
                  <td className="text-right tabular-nums text-muted">{p.schedule_strength.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <p className="text-muted text-xs mt-6 text-center">
        Data as of June 23, 2026 · power ratings from live 2026 results · API: {API}
      </p>
    </main>
  );
}
