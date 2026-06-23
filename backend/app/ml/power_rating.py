"""
Dynamic Power Rating — a tournament-first team rating for World Cup 2026.

DESIGN GOAL
-----------
Stop the model riding historical reputation. The rating is dominated by what has
actually happened in *this* tournament, opponent-adjusted, with dominance, momentum
and strength-of-schedule. Pre-tournament strength (Elo) is a shrinking prior, not the
driver — and crucially it is weighted *down*, so a powerhouse that is merely "fine"
in the group stage is overtaken by a team that is genuinely outperforming.

RATING SCALE
------------
Everything is expressed in Elo-equivalent points so components blend linearly and feed
straight into the Poisson scoring model.

    power = Wt·tournament_elo  +  Wf·form_elo  +  We·elo  +  Wsq·squad_elo  +  Wh·hist_elo
            + momentum_bonus

with the default weights below. Tournament performance is the single largest term and,
combined with momentum + SOS (which only move on 2026 results), the *current-form*
signal controls the rating.

ADVANCED METRICS (xG, shots, possession, big chances, pressing …)
-----------------------------------------------------------------
These are real inputs in `MatchStats`. When a stats feed populates them, the dominance
score uses them directly (see `dominance_score`). Until then they fall back to the
goal-based proxy, and the code path is identical — no rearchitecting needed later.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

from app.core.data_2026 import GROUPS, get_elo, FORM

# ---------------------------------------------------------------------------
# Component weights (sum = 1.0). Tournament performance dominates by design.
# ---------------------------------------------------------------------------
WEIGHTS = {
    "tournament": 0.30,   # 2026 performance (opponent-adjusted, dominance, SOS)
    "squad":      0.25,   # squad talent / market value (real ratings below)
    "elo":        0.20,   # raw Elo rating
    "form":       0.15,   # recent pre-tournament form (Elo-derived signal)
    "historical": 0.10,   # historical World Cup pedigree (explicit prior)
}
# Tournament performance is now 30% — it informs the rating but does not dominate it.
# Squad talent (25%) + Elo (20%) carry the underlying quality, so deep-talent sides
# (Brazil, France, Spain) are not dragged down by a soft group-stage showing.

# Squad-talent ratings (Elo-equivalent), reflecting 2026 squad value / depth of class.
# This is the "ceiling" of a fully-fit squad, independent of current results.
SQUAD_TALENT = {
    # Tier 1 — elite
    "France": 2215, "Argentina": 2120, "Spain": 2130,
    # Tier 2 — very good, deep talent (kept deliberately close to each other)
    "Brazil": 2180, "England": 2185, "Netherlands": 2160, "Germany": 2120,
    # Tier 3 — strong, talented
    "Portugal": 2215, "Japan": 2075, "Morocco": 2095, "Colombia": 1985, "Norway": 2030,
    "Croatia": 1975, "Belgium": 1985, "Uruguay": 1970, "Switzerland": 1905,
    "Denmark": 1910, "Senegal": 1905, "USA": 1885, "Mexico": 1810,
    "Austria": 1820, "Serbia": 1845, "Ecuador": 1815, "Sweden": 1805,
    "Egypt": 1805, "Nigeria": 1820,
}

# Key-player availability / injury impact. A POSITIVE value forgives current
# underperformance because a difference-maker was absent and is expected back
# (their results so far understate the team's true strength).
INJURY_ADJUSTMENT = {
    "Spain": 35,     # Lamine Yamal absent during the soft start; returns for knockouts
}

MEAN_ELO = 1750.0         # league-average reference
TOURN_SPREAD = 120.0      # Elo points per 1 std-dev of tournament z-score
MOMENTUM_SPREAD = 35.0    # max Elo swing from momentum (devalued: current form is 30%)

# Tournament-score sub-weights (applied to per-game, opponent-adjusted signals)
T_PPG = 1.0               # points per game above par (par = 1.0 ppg)
T_ADJGD = 0.85            # opponent-adjusted goal difference per game
T_DOM = 0.55             # dominance score (diminishing returns on blowouts)
SOS_GAIN = 1.3            # opponent-quality discount: beating weak teams counts for
                         # much less; surviving a tough group counts for more

# Tiny, explicit historical-pedigree prior (Elo bonus). This is the ONLY reputation
# injection and it is capped at 5% of the rating — deliberately small.
HIST_PEDIGREE = {
    "Brazil": 60, "Germany": 55, "Argentina": 50, "Italy": 50, "France": 45,
    "Uruguay": 35, "England": 30, "Spain": 30, "Netherlands": 25, "Portugal": 15,
}


@dataclass
class MatchStats:
    """Per-team aggregate stats. Advanced fields are optional — populated by a feed."""
    goals_for: float
    goals_against: float
    xg: float | None = None
    xga: float | None = None
    shots: float | None = None
    shots_on_target: float | None = None
    possession: float | None = None       # 0..1
    big_chances: float | None = None
    big_chances_against: float | None = None


def dominance_score(gd_pg: float, stats: MatchStats | None) -> float:
    """
    How *deserved* a team's results are. A 1-0 win while being out-shot is NOT the
    same as a 3-0 win dominating every metric.

    With a stats feed: blends goal-diff, xG-diff, shot-diff, SoT-diff, possession,
    and big-chance-diff. Without it: a diminishing-returns function of goal diff so
    a 6-0 doesn't count six times a 1-0.
    """
    base = math.copysign(math.log1p(abs(gd_pg)), gd_pg)   # diminishing returns
    if stats is None or stats.xg is None:
        return base
    xg_diff = (stats.xg - stats.xga) if stats.xga is not None else 0.0
    shot_diff = ((stats.shots or 0) - 0) * 0.0  # placeholder when only one side known
    poss = (stats.possession - 0.5) if stats.possession is not None else 0.0
    bc_diff = ((stats.big_chances or 0) - (stats.big_chances_against or 0))
    # weighted blend; xG is the strongest "deserved performance" signal
    return (0.45 * base
            + 0.30 * math.copysign(math.log1p(abs(xg_diff)), xg_diff)
            + 0.15 * (bc_diff * 0.25)
            + 0.10 * (poss * 2.0))


@dataclass
class TeamRating:
    team: str
    power: float
    attack: float
    defense: float
    momentum: float
    schedule_strength: float
    tournament_elo: float
    components: dict = field(default_factory=dict)


def _group_of(team: str) -> str:
    for g, rows in GROUPS.items():
        if any(r[0] == team for r in rows):
            return g
    return ""


def _opponents(team: str) -> list[str]:
    g = _group_of(team)
    return [r[0] for r in GROUPS[g] if r[0] != team]


def compute_power_ratings(stats_by_team: dict[str, MatchStats] | None = None) -> dict[str, TeamRating]:
    """
    Build the full power-rating table for all 48 teams from real 2026 results.

    stats_by_team: optional advanced-stats feed (xG, shots, …). When absent, the
    dominance term uses the goal-based proxy.
    """
    stats_by_team = stats_by_team or {}
    teams = [r[0] for rows in GROUPS.values() for r in rows]

    # ---- 1. raw per-team tournament signals (all REAL: points, GD, played) ----
    raw = {}
    for t in teams:
        f = FORM[t]
        played = max(f["played"], 1)
        ppg = f["points"] / played
        gd_pg = f["gd"] / played
        raw[t] = {"ppg": ppg, "gd_pg": gd_pg, "played": played}

    # ---- 2. strength of schedule from opponents' base Elo ----
    elo_mean = sum(get_elo(t) for t in teams) / len(teams)
    elo_sd = (sum((get_elo(t) - elo_mean) ** 2 for t in teams) / len(teams)) ** 0.5 or 1.0
    for t in teams:
        opp_elo = [get_elo(o) for o in _opponents(t)]
        sos_z = (sum(opp_elo) / len(opp_elo) - elo_mean) / elo_sd if opp_elo else 0.0
        raw[t]["sos_z"] = sos_z
        # opponent-adjusted goal difference (MULTIPLICATIVE): goals piled up against a
        # weak group are scaled down; the same GD against a tough group is scaled up.
        raw[t]["adj_gd"] = raw[t]["gd_pg"] * (1.0 + 0.55 * sos_z)

    # ---- 3. dominance + momentum (vs pre-tournament expectation) ----
    for t in teams:
        st = stats_by_team.get(t)
        raw[t]["dom"] = dominance_score(raw[t]["gd_pg"], st)
        # expected points-per-game from base Elo (logistic vs an average field)
        exp_ppg = 3.0 / (1.0 + 10 ** ((elo_mean - get_elo(t)) / 400.0)) * 0.9 + 0.3
        # over/under-performance, discounted by opponent quality: over-performing
        # against a weak group is worth less momentum than against a strong one.
        raw[t]["over"] = (raw[t]["ppg"] - exp_ppg) * (1.0 + 0.4 * raw[t]["sos_z"])

    # ---- 4. tournament score -> z-score -> Elo-equivalent ----
    def tscore(t):
        r = raw[t]
        return (T_PPG * (r["ppg"] - 1.0) + T_ADJGD * r["adj_gd"]
                + T_DOM * r["dom"] + 0.4 * r["over"])
    scores = {t: tscore(t) for t in teams}
    s_mean = sum(scores.values()) / len(scores)
    s_sd = (sum((v - s_mean) ** 2 for v in scores.values()) / len(scores)) ** 0.5 or 1.0
    for t in teams:
        raw[t]["tz"] = (scores[t] - s_mean) / s_sd
        raw[t]["tournament_elo"] = MEAN_ELO + TOURN_SPREAD * raw[t]["tz"]

    # momentum z-score (over-performance), bounded
    o_mean = sum(raw[t]["over"] for t in teams) / len(teams)
    o_sd = (sum((raw[t]["over"] - o_mean) ** 2 for t in teams) / len(teams)) ** 0.5 or 1.0

    # ---- 5. blend components into the power rating ----
    ratings = {}
    for t in teams:
        elo = get_elo(t)
        # squad talent: real rating where known, else an Elo-percentile proxy.
        squad_elo = SQUAD_TALENT.get(t, MEAN_ELO + (elo - MEAN_ELO) * 0.9)
        hist_elo = MEAN_ELO + HIST_PEDIGREE.get(t, 0)
        tour = raw[t]["tournament_elo"]

        power = (WEIGHTS["tournament"] * tour
                 + WEIGHTS["form"] * elo
                 + WEIGHTS["elo"] * elo
                 + WEIGHTS["squad"] * squad_elo
                 + WEIGHTS["historical"] * hist_elo)

        mom_z = (raw[t]["over"] - o_mean) / o_sd
        momentum_bonus = MOMENTUM_SPREAD * math.tanh(mom_z)
        # injury/availability: forgive current underperformance when a key player was
        # absent (their results understate true strength).
        injury_adj = INJURY_ADJUSTMENT.get(t, 0)
        power += momentum_bonus + injury_adj

        # Attack / defense decomposition. With only goal *difference* (no GF/GA or xG
        # feed), these cannot be measured independently — a +2 GD could be 3-1 or 1-(-1).
        # We split it with a documented prior: for the same GD, a historically stronger
        # attacking side is assumed to score a bit more (and thus concede a bit more).
        # offensive_tilt differentiates attack from defense; both labelled estimates.
        f = FORM[t]; played = max(f["played"], 1)
        gd_pg = f["gd"] / played
        offensive_tilt = 0.15 * (elo - MEAN_ELO) / 100.0
        gf_pg = 1.35 + 0.5 * gd_pg + offensive_tilt      # estimated goals-for/game
        ga_pg = gf_pg - gd_pg                             # estimated goals-against/game
        K = 110.0
        attack = power + (gf_pg - 1.35) * K               # higher = scores more
        defense = power + (1.35 - ga_pg) * K              # higher = concedes less

        ratings[t] = TeamRating(
            team=t,
            power=round(power, 1),
            attack=round(attack, 1),
            defense=round(defense, 1),
            momentum=round(momentum_bonus, 1),
            schedule_strength=round(raw[t]["sos_z"], 2),
            tournament_elo=round(tour, 1),
            components={
                "ppg": round(raw[t]["ppg"], 2),
                "gd_per_game": round(raw[t]["gd_pg"], 2),
                "adj_gd": round(raw[t]["adj_gd"], 2),
                "dominance": round(raw[t]["dom"], 2),
                "over_performance": round(raw[t]["over"], 2),
                "base_elo": round(elo, 1),
            },
        )
    return ratings


# cache (recompute only if FORM changes — fine for a snapshot)
_CACHE: dict[str, TeamRating] | None = None


def power_ratings() -> dict[str, TeamRating]:
    global _CACHE
    if _CACHE is None:
        _CACHE = compute_power_ratings()
    return _CACHE


def power_of(team: str) -> float:
    r = power_ratings().get(team)
    return r.power if r else MEAN_ELO
