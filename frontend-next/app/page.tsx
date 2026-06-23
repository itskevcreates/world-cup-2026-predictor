"use client";

import { useEffect, useState } from "react";

// Default to the live Railway backend so production works without extra config.
// Set NEXT_PUBLIC_API_URL to override (e.g. http://127.0.0.1:8000 for local dev).
const API =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://world-cup-2026-predictor-production-65ad.up.railway.app";

/* Semantic data hues — mirror the CSS tokens for inline-style use */
const C = {
  primary: "#2dd4a7",
  info: "#4aa3ff",
  accent: "#f6a609",
  violet: "#b08bff",
  danger: "#fb6a78",
  muted: "#91a0c2",
  faint: "#5f6e90",
};

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
  if (p >= 10) return { label: "Favorite", color: C.primary };
  if (p >= 4) return { label: "Contender", color: C.info };
  if (p > 0) return { label: "Dark horse", color: C.violet };
  return { label: "Outsider", color: C.faint };
}

/* ---------- Icons (Lucide-style, 1.75 stroke) ---------- */
const ico = (d: React.ReactNode) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);
const Icons = {
  swords: ico(<><polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5" /><line x1="13" y1="19" x2="19" y2="13" /><line x1="16" y1="16" x2="20" y2="20" /><line x1="19" y1="21" x2="21" y2="19" /></>),
  trophy: ico(<><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" /><path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" /><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" /><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" /></>),
  ticket: ico(<><path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z" /><path d="M13 5v14" strokeDasharray="2 2" /></>),
  gauge: ico(<><path d="m12 14 4-4" /><path d="M3.34 19a10 10 0 1 1 17.32 0" /></>),
  plus: ico(<><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>),
  database: ico(<><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14a9 3 0 0 0 18 0V5" /><path d="M3 12a9 3 0 0 0 18 0" /></>),
};

function Bar({ pct, color = C.primary }: { pct: number; color?: string }) {
  return (
    <div className="track h-1.5" role="presentation">
      <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} />
    </div>
  );
}

function Card({ title, eyebrow, icon, children, right, color = C.primary }: any) {
  return (
    <section className="card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-start gap-3 min-w-0">
          {icon && (
            <span className="shrink-0 grid place-items-center w-9 h-9 rounded-xl"
              style={{ background: `${color}1c`, color }}>{icon}</span>
          )}
          <div className="min-w-0">
            {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
            <h2 className="text-[15px] font-semibold leading-tight">{title}</h2>
          </div>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

function Stat({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div className="chip px-3.5 py-2.5 flex flex-col gap-0.5">
      <span className="num text-lg font-semibold leading-none" style={{ color }}>{value}</span>
      <span className="text-[11px] text-faint">{label}</span>
    </div>
  );
}

export default function Home() {
  const [teams, setTeams] = useState<TeamElo[]>([]);
  const [home, setHome] = useState("Spain");
  const [away, setAway] = useState("Brazil");
  const [pred, setPred] = useState<Prediction | null>(null);
  const [loadingPred, setLoadingPred] = useState(false);
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
    setLoadingPred(true);
    try {
      const r = await fetch(`${API}/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`);
      setPred(await r.json());
    } finally { setLoadingPred(false); }
  }
  async function simulate() {
    setLoadingSim(true);
    try {
      const d = await (await fetch(`${API}/simulate?n=50000`)).json();
      setOutlook((d.outlook as Outlook[]).filter((t) => t.title_pct > 0).slice(0, 16));
    } finally { setLoadingSim(false); }
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
    try {
      const r = await fetch(`${API}/parlay/matches`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ legs }),
      });
      setParlay(await r.json());
    } finally { setLoadingParlay(false); }
  }

  return (
    <div>
      {/* Sticky top bar */}
      <header className="sticky top-0 z-40 border-b border-line backdrop-blur-md"
        style={{ background: "rgba(8,11,22,0.72)" }}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="grid place-items-center w-8 h-8 rounded-lg"
              style={{ background: `${C.primary}1f`, color: C.primary }}>{Icons.trophy}</span>
            <span className="font-semibold text-[15px] tracking-tight">World Cup <span style={{ color: C.primary }}>2026</span></span>
          </div>
          <div className="flex items-center gap-2 chip px-2.5 py-1.5">
            <span className="live-dot" />
            <span className="text-[11px] text-muted">Live · Jun 23, 2026</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
        {/* Hero */}
        <section className="py-9 sm:py-12">
          <div className="eyebrow mb-3">USA · Mexico · Canada</div>
          <h1 className="text-[30px] sm:text-[42px] font-bold tracking-tight leading-[1.05] max-w-2xl">
            The numbers behind the <span style={{ color: C.primary }}>2026</span> World Cup.
          </h1>
          <p className="text-muted mt-3 text-sm max-w-xl leading-relaxed">
            Tournament-first power ratings and Monte Carlo simulation, trained on real historical
            results. Match odds, title outlook, and a model-priced betting slip.
          </p>
          <div className="flex flex-wrap gap-2.5 mt-6">
            <Stat value="49k" label="Matches trained" color={C.primary} />
            <Stat value="100k" label="Sims per run" color={C.info} />
            <Stat value="~60%" label="Outcome accuracy" color={C.accent} />
            <Stat value="48" label="Teams · 12 groups" color={C.violet} />
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2 items-start">
          {/* Match predictor */}
          <Card eyebrow="Single match" title="Match Predictor" icon={Icons.swords} color={C.info}>
            <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-center">
              <select aria-label="Home team" value={home} onChange={(e) => setHome(e.target.value)}>
                {teams.map((t) => <option key={t.team}>{t.team}</option>)}
              </select>
              <span className="text-faint text-[11px] font-medium px-0.5">vs</span>
              <select aria-label="Away team" value={away} onChange={(e) => setAway(e.target.value)}>
                {teams.map((t) => <option key={t.team}>{t.team}</option>)}
              </select>
            </div>
            <button className="btn-primary w-full justify-center mt-2.5" onClick={predict} disabled={loadingPred}>
              {loadingPred ? "Predicting…" : "Predict outcome"}
            </button>

            {loadingPred && !pred && (
              <div className="mt-5 space-y-3">
                {[0, 1, 2].map((i) => <div key={i} className="skeleton h-7" />)}
              </div>
            )}
            {pred && (
              <div className="mt-5 space-y-3.5">
                <div className="flex items-center justify-between text-sm">
                  <b className="truncate">{pred.home}</b>
                  <span className="chip num text-[11px] text-muted px-2 py-1 shrink-0 mx-2">
                    xG {pred.expected_goals.home.toFixed(2)} – {pred.expected_goals.away.toFixed(2)}
                  </span>
                  <b className="truncate text-right">{pred.away}</b>
                </div>
                {[
                  { l: `${pred.home} win`, v: pred.probabilities.home_win, c: C.primary },
                  { l: "Draw", v: pred.probabilities.draw, c: C.info },
                  { l: `${pred.away} win`, v: pred.probabilities.away_win, c: C.violet },
                ].map((r) => (
                  <div key={r.l}>
                    <div className="flex justify-between text-[13px] mb-1.5">
                      <span className="text-muted">{r.l}</span>
                      <span className="num font-medium">{(r.v * 100).toFixed(1)}%</span>
                    </div>
                    <Bar pct={r.v * 100} color={r.c} />
                  </div>
                ))}
                <div className="flex items-center gap-2 pt-1 flex-wrap">
                  <span className="eyebrow">Likely scores</span>
                  {pred.most_likely_scorelines.map((s) => (
                    <span key={s.score} className="chip num text-xs px-2 py-0.5 text-muted">{s.score}</span>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Title outlook */}
          <Card eyebrow="50,000 simulations" title="Title Outlook" icon={Icons.trophy} color={C.primary}
            right={<button className="btn-primary" onClick={simulate} disabled={loadingSim}>
              {loadingSim ? "Simulating…" : "Run"}
            </button>}>
            {outlook.length === 0 ? (
              loadingSim ? (
                <div className="space-y-2.5">{[...Array(6)].map((_, i) => <div key={i} className="skeleton h-7" />)}</div>
              ) : (
                <div className="text-center py-8">
                  <div className="text-3xl mb-2" style={{ color: C.faint }}>○</div>
                  <p className="text-muted text-sm">Run the Monte Carlo to see championship odds.</p>
                </div>
              )
            ) : (
              <div className="overflow-x-auto -mx-1">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="eyebrow text-left">
                      <th className="pb-2.5 font-semibold pl-1">Team</th>
                      <th className="pb-2.5 font-semibold text-right">SF</th>
                      <th className="pb-2.5 font-semibold text-right pr-3">Final</th>
                      <th className="pb-2.5 font-semibold">Title</th>
                    </tr>
                  </thead>
                  <tbody>
                    {outlook.map((o, i) => {
                      const t = tier(o.title_pct); const max = outlook[0].title_pct;
                      return (
                        <tr key={o.team} className="row-div t-row">
                          <td className="py-2 pl-1">
                            <span className="num text-faint text-xs mr-2">{i + 1}</span>
                            <span className="font-medium">{o.team}</span>
                            <span className="pill ml-2" style={{ background: `${t.color}1e`, color: t.color }}>{t.label}</span>
                          </td>
                          <td className="text-right num text-muted">{o.semi_pct}%</td>
                          <td className="text-right num text-muted pr-3">{o.final_pct}%</td>
                          <td>
                            <div className="flex items-center gap-2">
                              <div className="flex-1 min-w-[44px]"><Bar pct={(o.title_pct / max) * 100} color={t.color} /></div>
                              <span className="num w-12 text-right font-semibold" style={{ color: t.color }}>{o.title_pct}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* Parlay */}
        <div className="mt-4">
          <Card eyebrow="Betting slip" title="Parlay Simulator" icon={Icons.ticket} color={C.accent}>
            <p className="text-muted text-[13px] -mt-1 mb-4 leading-relaxed">
              Head-to-head picks priced by the power-rating model. Matches are treated as
              independent — the parlay is the product of each leg.
            </p>
            <div className="space-y-2">
              {legs.map((leg, i) => {
                const lr = parlay?.legs?.[i];
                return (
                  <div key={i} className="chip p-2 grid grid-cols-[1fr_auto_1fr_1fr_auto_auto] gap-2 items-center">
                    <select aria-label={`Leg ${i + 1} home`} value={leg.home} onChange={(e) => setLeg(i, "home", e.target.value)}>
                      {teams.map((t) => <option key={t.team}>{t.team}</option>)}
                    </select>
                    <span className="text-faint text-[11px]">vs</span>
                    <select aria-label={`Leg ${i + 1} away`} value={leg.away} onChange={(e) => setLeg(i, "away", e.target.value)}>
                      {teams.map((t) => <option key={t.team}>{t.team}</option>)}
                    </select>
                    <select aria-label={`Leg ${i + 1} pick`} value={leg.pick} onChange={(e) => setLeg(i, "pick", e.target.value)}>
                      <option value="home">{leg.home}</option>
                      <option value="draw">Draw</option>
                      <option value="away">{leg.away}</option>
                    </select>
                    <span className="num text-sm w-12 text-right font-semibold" style={{ color: lr ? C.primary : C.faint }}>
                      {lr ? `${(lr.probability * 100).toFixed(0)}%` : "—"}
                    </span>
                    <button onClick={() => removeLeg(i)} aria-label={`Remove leg ${i + 1}`}
                      className="text-faint hover:text-danger w-7 h-7 grid place-items-center rounded-md transition-colors text-lg leading-none">×</button>
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              <button className="btn-ghost text-sm" onClick={addLeg}>{Icons.plus} Add match</button>
              <button className="btn-primary" onClick={calcParlay} disabled={loadingParlay || legs.length === 0}>
                {loadingParlay ? "Calculating…" : "Calculate parlay"}
              </button>
            </div>

            {parlay && (
              <div className="mt-5 pt-5 row-div">
                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="chip p-4" style={{ background: `${C.primary}12`, borderColor: `${C.primary}33` }}>
                    <div className="eyebrow mb-1.5">All picks correct</div>
                    <div className="num text-4xl font-bold leading-none" style={{ color: C.primary }}>
                      {(parlay.parlay_probability * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="chip p-4">
                    <div className="eyebrow mb-1.5">Fair odds</div>
                    <div className="num text-3xl font-bold leading-none" style={{ color: C.accent }}>
                      {parlay.fair_decimal_odds}×
                    </div>
                    <div className="num text-muted text-xs mt-1.5">
                      {parlay.fair_american_odds > 0 ? "+" : ""}{parlay.fair_american_odds} American
                    </div>
                  </div>
                </div>
                <table className="w-full text-sm mt-4">
                  <tbody>
                    {parlay.legs.map((l: any, i: number) => (
                      <tr key={i} className="row-div t-row">
                        <td className="py-2 font-medium">{l.match}</td>
                        <td className="text-muted text-[13px]">{l.pick}</td>
                        <td className="text-right num font-medium">{(l.probability * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* Power ratings */}
        <div className="mt-4">
          <Card eyebrow="Tournament-first · 30% current form, 70% talent & prior"
            title="Dynamic Power Ratings" icon={Icons.gauge} color={C.violet}>
            {powers.length === 0 ? (
              <div className="space-y-2.5">{[...Array(8)].map((_, i) => <div key={i} className="skeleton h-7" />)}</div>
            ) : (
              <div className="overflow-x-auto -mx-1">
                <table className="w-full text-sm min-w-[460px]">
                  <thead>
                    <tr className="eyebrow text-left">
                      <th className="pb-2.5 font-semibold pl-1">#</th>
                      <th className="pb-2.5 font-semibold">Team</th>
                      <th className="pb-2.5 font-semibold text-right">Power</th>
                      <th className="pb-2.5 font-semibold text-right">Atk</th>
                      <th className="pb-2.5 font-semibold text-right">Def</th>
                      <th className="pb-2.5 font-semibold text-right">Mom</th>
                      <th className="pb-2.5 font-semibold text-right pr-1">SOS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {powers.slice(0, 16).map((p, i) => {
                      const max = powers[0].power;
                      return (
                        <tr key={p.team} className="row-div t-row">
                          <td className="py-2 num text-faint text-xs pl-1">{i + 1}</td>
                          <td className="font-medium">{p.team}</td>
                          <td className="text-right">
                            <div className="inline-flex items-center gap-2">
                              <div className="w-12 hidden sm:block"><Bar pct={(p.power / max) * 100} color={C.violet} /></div>
                              <span className="num font-semibold w-7 text-right">{p.power.toFixed(0)}</span>
                            </div>
                          </td>
                          <td className="text-right num text-muted">{p.attack.toFixed(0)}</td>
                          <td className="text-right num text-muted">{p.defense.toFixed(0)}</td>
                          <td className="text-right num font-medium" style={{ color: p.momentum >= 0 ? C.primary : C.danger }}>
                            {p.momentum >= 0 ? "+" : ""}{p.momentum.toFixed(0)}
                          </td>
                          <td className="text-right num text-muted pr-1">{p.schedule_strength.toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <footer className="mt-10 pt-6 border-t border-line flex flex-wrap items-center justify-between gap-3">
          <p className="text-faint text-xs flex items-center gap-2">
            <span style={{ color: C.violet }}>{Icons.database}</span>
            Data as of June 23, 2026 · power ratings from live 2026 results
          </p>
          <p className="text-faint text-xs">
            Squad-talent values are judgment calls · no live xG feed
          </p>
        </footer>
      </main>
    </div>
  );
}
