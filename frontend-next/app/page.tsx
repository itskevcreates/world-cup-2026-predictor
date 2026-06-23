"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type TeamElo = { team: string };
type Prediction = {
  home: string; away: string;
  expected_goals: { home: number; away: number };
  probabilities: { home_win: number; draw: number; away_win: number };
  most_likely_scorelines: { score: string; prob: number }[];
};
type Power = {
  team: string; power: number; attack: number; defense: number;
  momentum: number; schedule_strength: number;
};
type Outlook = {
  team: string; advance_pct: number; quarter_pct: number;
  semi_pct: number; final_pct: number; title_pct: number;
};

function tier(p: number) {
  if (p >= 10) return { label: "Favorite", color: "#22d3a6" };
  if (p >= 4) return { label: "Contender", color: "#5b9dff" };
  if (p > 0) return { label: "Dark horse", color: "#c084fc" };
  return { label: "Outsider", color: "#64748b" };
}

function Bar({ pct, color = "#22d3a6" }: { pct: number; color?: string }) {
  return (
    <div className="track h-1.5">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function Card({ title, eyebrow, children, right }: any) {
  return (
    <section className="card p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
          <h2 className="text-[15px] font-semibold">{title}</h2>
        </div>
        {right}
      </div>
      {children}
    </section>
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

  type Leg = { home: string; away: string; pick: "home" | "draw" | "away" };
  const [legs, setLegs] = useState<Leg[]>([
    { home: "Colombia", away: "DR Congo", pick: "home" },
    { home: "Portugal", away: "Uzbekistan", pick: "home" },
  ]);
  const [parlay, setParlay] = useState<any>(null);
  const [loadingParlay, setLoadingParlay] = useState(false);

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
    const d = await (await fetch(`${API}/simulate?n=50000`)).json();
    setOutlook((d.outlook as Outlook[]).filter((t) => t.title_pct > 0).slice(0, 16));
    setLoadingSim(false);
  }
  function setLeg(i: number, f: keyof Leg, v: string) {
    setLegs((ls) => ls.map((l, j) => (j === i ? { ...l, [f]: v } : l)));
  }
  function addLeg() {
    setLegs((ls) => [...ls, { home: teams[0]?.team || "Spain", away: teams[1]?.team || "Brazil", pick: "home" }]);
  }
  function removeLeg(i: number) { setLegs((ls) => ls.filter((_, j) => j !== i)); }
  async function calcParlay() {
    setLoadingParlay(true);
    const r = await fetch(`${API}/parlay/matches`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ legs }),
    });
    setParlay(await r.json());
    setLoadingParlay(false);
  }

  const sel = "min-w-0";

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 pb-20">
      {/* Header */}
      <header className="py-10 text-center">
        <div className="eyebrow mb-2">USA · Mexico · Canada · June 2026</div>
        <h1 className="text-[28px] sm:text-4xl font-bold tracking-tight">
          World Cup 2026 <span className="text-[#22d3a6]">Prediction Platform</span>
        </h1>
        <p className="text-[#8093b8] mt-2 text-sm">
          Tournament-first power ratings · Monte Carlo simulation · trained on 49k matches
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Match predictor */}
        <Card eyebrow="Single match" title="Match Predictor">
          <div className="grid grid-cols-[1fr_auto_1fr_auto] gap-2 items-center">
            <select className={sel} value={home} onChange={(e) => setHome(e.target.value)}>
              {teams.map((t) => <option key={t.team}>{t.team}</option>)}
            </select>
            <span className="text-[#6b7da3] text-xs px-1">vs</span>
            <select className={sel} value={away} onChange={(e) => setAway(e.target.value)}>
              {teams.map((t) => <option key={t.team}>{t.team}</option>)}
            </select>
            <button className="btn-primary" onClick={predict}>Predict</button>
          </div>
          {pred && (
            <div className="mt-5 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <b>{pred.home}</b>
                <span className="text-[#8093b8] text-xs">
                  xG {pred.expected_goals.home} – {pred.expected_goals.away}
                </span>
                <b>{pred.away}</b>
              </div>
              {[
                { l: `${pred.home} win`, v: pred.probabilities.home_win, c: "#22d3a6" },
                { l: "Draw", v: pred.probabilities.draw, c: "#5b9dff" },
                { l: `${pred.away} win`, v: pred.probabilities.away_win, c: "#c084fc" },
              ].map((r) => (
                <div key={r.l}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{r.l}</span><span className="tabular-nums">{(r.v * 100).toFixed(1)}%</span>
                  </div>
                  <Bar pct={r.v * 100} color={r.c} />
                </div>
              ))}
              <div className="text-[#8093b8] text-xs pt-1">
                Likely scores · {pred.most_likely_scorelines.map((s) => s.score).join("  ")}
              </div>
            </div>
          )}
        </Card>

        {/* Title outlook */}
        <Card eyebrow="50,000 simulations" title="Title Outlook"
          right={<button className="btn-primary" onClick={simulate} disabled={loadingSim}>
            {loadingSim ? "Simulating…" : "Run"}
          </button>}>
          {outlook.length === 0 ? (
            <p className="text-[#8093b8] text-sm">Run the Monte Carlo to see championship odds.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="eyebrow text-left">
                  <th className="pb-2 font-semibold">Team</th>
                  <th className="pb-2 font-semibold text-right">SF</th>
                  <th className="pb-2 font-semibold text-right pr-3">Final</th>
                  <th className="pb-2 font-semibold">Win</th>
                </tr>
              </thead>
              <tbody>
                {outlook.map((o, i) => {
                  const t = tier(o.title_pct); const max = outlook[0].title_pct;
                  return (
                    <tr key={o.team} className="row-div">
                      <td className="py-1.5">
                        <span className="text-[#6b7da3] mr-2 tabular-nums text-xs">{i + 1}</span>{o.team}
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full"
                          style={{ background: `${t.color}1e`, color: t.color }}>{t.label}</span>
                      </td>
                      <td className="text-right tabular-nums text-[#8093b8]">{o.semi_pct}%</td>
                      <td className="text-right tabular-nums text-[#8093b8] pr-3">{o.final_pct}%</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 min-w-[50px]"><Bar pct={(o.title_pct / max) * 100} color={t.color} /></div>
                          <span className="tabular-nums w-12 text-right font-medium">{o.title_pct}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      {/* Parlay */}
      <div className="mt-4">
        <Card eyebrow="Betting slip" title="Parlay Simulator">
          <p className="text-[#8093b8] text-xs -mt-2 mb-4">
            Head-to-head picks priced by the power-rating model. Matches are independent —
            the parlay is the product of each leg.
          </p>
          <div className="space-y-2">
            {legs.map((leg, i) => {
              const lr = parlay?.legs?.[i];
              return (
                <div key={i} className="grid grid-cols-[1fr_auto_1fr_auto_auto_auto] gap-2 items-center">
                  <select value={leg.home} onChange={(e) => setLeg(i, "home", e.target.value)}>
                    {teams.map((t) => <option key={t.team}>{t.team}</option>)}
                  </select>
                  <span className="text-[#6b7da3] text-xs">vs</span>
                  <select value={leg.away} onChange={(e) => setLeg(i, "away", e.target.value)}>
                    {teams.map((t) => <option key={t.team}>{t.team}</option>)}
                  </select>
                  <select value={leg.pick} onChange={(e) => setLeg(i, "pick", e.target.value)}>
                    <option value="home">{leg.home}</option>
                    <option value="draw">Draw</option>
                    <option value="away">{leg.away}</option>
                  </select>
                  <span className="text-[#22d3a6] text-sm tabular-nums w-12 text-right">
                    {lr ? `${(lr.probability * 100).toFixed(0)}%` : ""}
                  </span>
                  <button onClick={() => removeLeg(i)} aria-label="remove"
                    className="text-[#6b7da3] hover:text-red-400 px-1 text-lg leading-none">×</button>
                </div>
              );
            })}
          </div>
          <div className="flex gap-2 mt-4">
            <button className="btn-ghost text-sm" onClick={addLeg}>+ Add match</button>
            <button className="btn-primary" onClick={calcParlay} disabled={loadingParlay || legs.length === 0}>
              {loadingParlay ? "Calculating…" : "Calculate Parlay"}
            </button>
          </div>

          {parlay && (
            <div className="mt-5 pt-4 row-div">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <div className="eyebrow mb-1">All picks correct</div>
                  <div className="text-4xl font-bold text-[#22d3a6] tabular-nums leading-none">
                    {(parlay.parlay_probability * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="text-right">
                  <div className="eyebrow mb-1">Fair odds</div>
                  <div className="tabular-nums text-lg">
                    {parlay.fair_decimal_odds}×
                    <span className="text-[#8093b8] text-sm ml-1">
                      ({parlay.fair_american_odds > 0 ? "+" : ""}{parlay.fair_american_odds})
                    </span>
                  </div>
                </div>
              </div>
              <table className="w-full text-sm mt-4">
                <tbody>
                  {parlay.legs.map((l: any, i: number) => (
                    <tr key={i} className="row-div">
                      <td className="py-1.5">{l.match}</td>
                      <td className="text-[#8093b8]">{l.pick}</td>
                      <td className="text-right tabular-nums">{(l.probability * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {/* Power ratings */}
      {powers.length > 0 && (
        <div className="mt-4">
          <Card eyebrow="Tournament-first · 30% current form, 70% talent & prior" title="Dynamic Power Ratings">
            <table className="w-full text-sm">
              <thead>
                <tr className="eyebrow text-left">
                  <th className="pb-2 font-semibold">#</th>
                  <th className="pb-2 font-semibold">Team</th>
                  <th className="pb-2 font-semibold text-right">Power</th>
                  <th className="pb-2 font-semibold text-right">Atk</th>
                  <th className="pb-2 font-semibold text-right">Def</th>
                  <th className="pb-2 font-semibold text-right">Mom</th>
                  <th className="pb-2 font-semibold text-right">SOS</th>
                </tr>
              </thead>
              <tbody>
                {powers.slice(0, 16).map((p, i) => (
                  <tr key={p.team} className="row-div">
                    <td className="py-1.5 text-[#6b7da3] tabular-nums text-xs">{i + 1}</td>
                    <td>{p.team}</td>
                    <td className="text-right tabular-nums font-medium">{p.power.toFixed(0)}</td>
                    <td className="text-right tabular-nums text-[#8093b8]">{p.attack.toFixed(0)}</td>
                    <td className="text-right tabular-nums text-[#8093b8]">{p.defense.toFixed(0)}</td>
                    <td className="text-right tabular-nums" style={{ color: p.momentum >= 0 ? "#22d3a6" : "#f87171" }}>
                      {p.momentum >= 0 ? "+" : ""}{p.momentum.toFixed(0)}
                    </td>
                    <td className="text-right tabular-nums text-[#8093b8]">{p.schedule_strength.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      <p className="text-[#6b7da3] text-xs mt-8 text-center">
        Data as of June 23, 2026 · power ratings from live 2026 results
      </p>
    </main>
  );
}
