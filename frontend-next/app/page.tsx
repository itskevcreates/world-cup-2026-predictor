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
type TitleOdds = { team: string; title_pct: number };

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
  const [odds, setOdds] = useState<TitleOdds[]>([]);
  const [loadingSim, setLoadingSim] = useState(false);

  useEffect(() => {
    fetch(`${API}/teams`).then((r) => r.json()).then(setTeams).catch(() => {});
  }, []);

  async function predict() {
    const r = await fetch(`${API}/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`);
    setPred(await r.json());
  }

  async function simulate() {
    setLoadingSim(true);
    const r = await fetch(`${API}/simulate?n=10000`);
    const d = await r.json();
    setOdds(d.title_odds.slice(0, 12));
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
          <h2 className="font-semibold mb-3">Tournament Simulation</h2>
          <button onClick={simulate} disabled={loadingSim}
            className="bg-accent text-[#04231a] font-bold rounded-lg px-4 py-2">
            {loadingSim ? "Running 10,000 sims…" : "Run Monte Carlo (10,000)"}
          </button>
          {odds.length > 0 && (
            <table className="w-full mt-4 text-sm">
              <thead>
                <tr className="text-muted text-left">
                  <th className="py-1">Team</th><th>Title chance</th><th></th>
                </tr>
              </thead>
              <tbody>
                {odds.map((o) => (
                  <tr key={o.team}>
                    <td className="py-1">{o.team}</td>
                    <td className="w-1/2">
                      <div className="h-2 rounded bg-[#0e1530] overflow-hidden">
                        <div className="h-full bg-accent" style={{ width: `${Math.min(100, o.title_pct * 3)}%` }} />
                      </div>
                    </td>
                    <td className="tabular-nums">{o.title_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <p className="text-muted text-xs mt-6 text-center">
        Data as of June 23, 2026 · Elo learned from 49k historical matches · API: {API}
      </p>
    </main>
  );
}
