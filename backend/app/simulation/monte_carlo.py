"""
Monte Carlo tournament simulator for World Cup 2026.

Strategy
--------
The group stage is already 2/3 complete (real standings are the starting point).
For each simulation run we:
  1. Play the remaining matchday-3 group games (random Poisson scorelines).
  2. Rank each group -> top 2 advance, plus the 8 best 3rd-placed teams (2026 format).
  3. Play a 32-team single-elimination knockout to a champion.
Repeating this many times, the fraction of runs each team wins = its title probability.

Randomness comes from drawing actual scorelines from each team's Poisson lambda,
so stronger teams win more often but upsets happen — exactly like the real thing.
"""
from __future__ import annotations
import random
from collections import defaultdict

from app.core.data_2026 import GROUPS, get_strength
from app.ml.poisson_model import expected_goals

# Canonical matchday-3 pairings for a group ordered [0,1,2,3]:
# round 3 pits index 0 v 3 and 1 v 2 (rounds 1 and 2 already played).
REMAINING_PAIRS = [(0, 3), (1, 2)]


def _sample_goals(lam: float, rng: random.Random) -> int:
    """Draw a goal count from a Poisson(lam) distribution (Knuth's algorithm)."""
    L, k, p = 2.718281828 ** (-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def _play(home: str, away: str, rng: random.Random, knockout: bool = False):
    """Simulate one match. Returns (home_goals, away_goals, winner)."""
    lam_h, lam_a = expected_goals(get_strength(home), get_strength(away))
    gh, ga = _sample_goals(lam_h, rng), _sample_goals(lam_a, rng)
    if gh > ga:
        winner = home
    elif ga > gh:
        winner = away
    else:
        if knockout:
            # extra time / penalties: settle by Elo-weighted coin flip
            ph = get_strength(home) / (get_strength(home) + get_strength(away))
            winner = home if rng.random() < ph else away
        else:
            winner = None  # a draw is allowed in the group stage
    return gh, ga, winner


def _simulate_groups(rng: random.Random):
    """Return (winners, runners_up, third_places) after finishing the group stage."""
    standings = {}  # group -> {team: [points, gd]}
    for g, teams in GROUPS.items():
        table = {name: [pts, gd] for (name, pts, gd, _played) in teams}
        names = [t[0] for t in teams]
        for i, j in REMAINING_PAIRS:
            h, a = names[i], names[j]
            gh, ga, winner = _play(h, a, rng)
            table[h][1] += gh - ga
            table[a][1] += ga - gh
            if winner is None:
                table[h][0] += 1
                table[a][0] += 1
            elif winner == h:
                table[h][0] += 3
            else:
                table[a][0] += 3
        ranked = sorted(names, key=lambda n: (table[n][0], table[n][1]), reverse=True)
        standings[g] = (ranked, table)

    winners, runners, thirds = {}, {}, []
    for g, (ranked, table) in standings.items():
        winners[g] = ranked[0]
        runners[g] = ranked[1]
        thirds.append((g, ranked[2], table[ranked[2]][0], table[ranked[2]][1]))

    # best 8 third-placed teams by (points, gd)
    thirds.sort(key=lambda x: (x[2], x[3]), reverse=True)
    best_thirds = [t[1] for t in thirds[:8]]
    return list(winners.values()), list(runners.values()), best_thirds


def _knockout(qualifiers: list[str], rng: random.Random, reached: dict) -> str:
    """Single-elimination from 32 -> champion. Records how far each team gets."""
    bracket = qualifiers[:]
    rng.shuffle(bracket)
    # stage label keyed by how many teams remain at the start of a round
    stage = {16: "r16", 8: "quarter", 4: "semi", 2: "final"}
    while len(bracket) > 1:
        nxt = []
        for i in range(0, len(bracket), 2):
            _, _, w = _play(bracket[i], bracket[i + 1], rng, knockout=True)
            nxt.append(w)
        bracket = nxt
        label = stage.get(len(bracket))
        if label:
            for t in bracket:
                reached[label][t] += 1
    return bracket[0]


def simulate_once(rng: random.Random, reached: dict):
    winners, runners, thirds = _simulate_groups(rng)
    qualifiers = winners + runners + thirds  # 12 + 12 + 8 = 32
    champion = _knockout(qualifiers, rng, reached)
    return champion, set(qualifiers)


def run_simulations(n: int = 10000, seed: int | None = None) -> dict:
    """Run n tournament simulations; return aggregated round-by-round probabilities."""
    rng = random.Random(seed)
    titles = defaultdict(int)
    advance = defaultdict(int)
    reached = {k: defaultdict(int) for k in ("r16", "quarter", "semi", "final")}
    for _ in range(n):
        champ, qualifiers = simulate_once(rng, reached)
        titles[champ] += 1
        for t in qualifiers:
            advance[t] += 1

    def pct(c):
        return round(100 * c / n, 1)

    # one consolidated table: every team that ever advanced, with full path odds
    teams = set(advance) | set(titles)
    table = [{
        "team": t,
        "advance_pct": pct(advance[t]),
        "quarter_pct": pct(reached["quarter"][t]),
        "semi_pct": pct(reached["semi"][t]),
        "final_pct": pct(reached["final"][t]),
        "title_pct": pct(titles[t]),
    } for t in teams]
    table.sort(key=lambda x: (x["title_pct"], x["semi_pct"], x["advance_pct"]), reverse=True)

    return {
        "simulations": n,
        "title_odds": [{"team": r["team"], "title_pct": r["title_pct"]} for r in table],
        "advance_odds": sorted(
            ({"team": t, "advance_pct": pct(c)} for t, c in advance.items()),
            key=lambda x: x["advance_pct"], reverse=True),
        "outlook": table,  # full round-by-round odds for the polished UI
    }
