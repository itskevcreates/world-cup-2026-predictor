"""
Match prediction model: Elo -> expected goals -> Poisson scoreline distribution.

How it works
------------
1. Each team has an Elo strength rating. The Elo *difference* sets how many goals
   we expect each side to score (goal "supremacy").
2. Goals in soccer are well-modelled by a Poisson distribution (rare, independent
   events over 90 minutes). So we turn expected goals (lambda) into a full
   probability distribution over scorelines 0-0, 1-0, 2-1, ...
3. Summing the scoreline grid gives P(home win) / P(draw) / P(away win).

This is the classic, battle-tested approach to football modelling (a simplified
Dixon-Coles). It needs no training download — strength comes from the Elo ratings.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

from app.core.data_2026 import get_elo

# --- model constants (tuned to realistic international scoring) ---------------
BASE_GOALS = 1.35     # avg goals a balanced team scores in a WC match
ELO_SCALE = 360.0     # how sharply Elo gap converts to goals (smaller = sharper)
MAX_GOALS = 10        # truncate the scoreline grid here (P beyond is negligible)


def expected_goals(elo_a: float, elo_b: float, neutral: bool = True) -> tuple[float, float]:
    """Expected goals for A and B given their Elo ratings."""
    diff = (elo_a - elo_b) / ELO_SCALE
    lam_a = BASE_GOALS * math.exp(diff)
    lam_b = BASE_GOALS * math.exp(-diff)
    return lam_a, lam_b


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


@dataclass
class MatchPrediction:
    home: str
    away: str
    lam_home: float
    lam_away: float
    p_home: float
    p_draw: float
    p_away: float
    top_scorelines: list = field(default_factory=list)

    def as_dict(self):
        return {
            "home": self.home,
            "away": self.away,
            "expected_goals": {"home": round(self.lam_home, 2), "away": round(self.lam_away, 2)},
            "probabilities": {
                "home_win": round(self.p_home, 3),
                "draw": round(self.p_draw, 3),
                "away_win": round(self.p_away, 3),
            },
            "most_likely_scorelines": self.top_scorelines,
        }


def predict_match(home: str, away: str) -> MatchPrediction:
    """Full probabilistic prediction for a single match."""
    lam_h, lam_a = expected_goals(get_elo(home), get_elo(away))

    p_home = p_draw = p_away = 0.0
    grid = []
    for h in range(MAX_GOALS + 1):
        ph = _poisson_pmf(h, lam_h)
        for a in range(MAX_GOALS + 1):
            p = ph * _poisson_pmf(a, lam_a)
            grid.append(((h, a), p))
            if h > a:
                p_home += p
            elif h == a:
                p_draw += p
            else:
                p_away += p

    grid.sort(key=lambda x: x[1], reverse=True)
    top = [{"score": f"{h}-{a}", "prob": round(p, 3)} for (h, a), p in grid[:5]]

    return MatchPrediction(home, away, lam_h, lam_a, p_home, p_draw, p_away, top)
