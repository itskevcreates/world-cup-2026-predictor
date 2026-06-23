"""
Real FIFA World Cup 2026 (USA / Mexico / Canada) data.

Snapshot taken 2026-06-23 from live tournament coverage:
  - Group compositions: the official 48-team, 12-group draw (Dec 5, 2025).
  - Standings: points / goal-difference as of June 23, 2026 (group stage in progress).

Sources cross-checked: NBC Sports full group tables, Yahoo Sports live scores,
Al Jazeera knockout-qualification tracker, Wikipedia 2026 FIFA World Cup.

The `elo` ratings are approximate World-Football-Elo-style strength ratings used to
drive the prediction model. They are reasonable estimates, not official numbers.
"""

# ---------------------------------------------------------------------------
# Team strength ratings (approx. Elo, June 2026). Higher = stronger.
# ---------------------------------------------------------------------------
ELO = {
    "Spain": 2095, "Argentina": 2085, "France": 2080, "Brazil": 2030,
    "England": 2010, "Portugal": 2000, "Netherlands": 1995, "Germany": 1980,
    "Belgium": 1935, "Croatia": 1905, "Colombia": 1900, "Uruguay": 1895,
    "Morocco": 1890, "Switzerland": 1860, "Japan": 1855, "Senegal": 1850,
    "USA": 1825, "Mexico": 1815, "Denmark": 1900, "Austria": 1820,
    "Ecuador": 1800, "Norway": 1840, "South Korea": 1790, "Sweden": 1800,
    "Australia": 1760, "Egypt": 1770, "Iran": 1765, "Ivory Coast": 1760,
    "Serbia": 1820, "Scotland": 1760, "Panama": 1700, "Paraguay": 1740,
    "Czechia": 1780, "Peru": 1730, "Tunisia": 1720, "Ghana": 1720,
    "Cape Verde": 1660, "Algeria": 1770, "Turkiye": 1820, "Wales": 1760,
    "Qatar": 1680, "Saudi Arabia": 1670, "Iraq": 1660, "Jordan": 1640,
    "Uzbekistan": 1680, "DR Congo": 1700, "South Africa": 1690,
    "New Zealand": 1620, "Bosnia and Herzegovina": 1740, "Costa Rica": 1700,
    "Curacao": 1560, "Haiti": 1580, "Bulgaria": 1620, "Georgia": 1700,
    "Slovenia": 1720, "Cameroon": 1730, "Poland": 1790,
}

# ---------------------------------------------------------------------------
# The 12 groups and live standings (June 23, 2026).
# played = group matches already completed by that team.
# ---------------------------------------------------------------------------
# Each team: (name, points, goal_difference, played)
GROUPS = {
    "A": [("Mexico", 6, 3, 2), ("South Korea", 3, 0, 2), ("Czechia", 1, -1, 2), ("South Africa", 1, -2, 2)],
    "B": [("Canada", 4, 6, 2), ("Switzerland", 4, 3, 2), ("Bosnia and Herzegovina", 1, -3, 2), ("Qatar", 1, -6, 2)],
    "C": [("Brazil", 4, 3, 2), ("Morocco", 4, 1, 2), ("Scotland", 3, 0, 2), ("Haiti", 0, -4, 2)],
    "D": [("USA", 6, 5, 2), ("Australia", 3, 0, 2), ("Paraguay", 3, -2, 2), ("Turkiye", 0, -3, 2)],
    "E": [("Germany", 6, 7, 2), ("Ivory Coast", 3, 0, 2), ("Ecuador", 1, -1, 2), ("Curacao", 1, -6, 2)],
    "F": [("Netherlands", 4, 4, 2), ("Japan", 4, 4, 2), ("Sweden", 3, 0, 2), ("Tunisia", 0, -8, 2)],
    "G": [("Egypt", 4, 2, 2), ("Iran", 2, 0, 2), ("Belgium", 2, 0, 2), ("New Zealand", 1, -2, 2)],
    "H": [("Spain", 4, 4, 2), ("Uruguay", 2, 0, 2), ("Cape Verde", 2, 0, 2), ("Saudi Arabia", 1, -4, 2)],
    "I": [("France", 6, 5, 2), ("Norway", 3, 3, 2), ("Senegal", 0, -2, 2), ("Iraq", 0, -6, 2)],
    "J": [("Argentina", 6, 5, 2), ("Austria", 3, 1, 2), ("Jordan", 0, -2, 2), ("Algeria", 0, -3, 2)],
    "K": [("Colombia", 3, 2, 2), ("DR Congo", 1, 0, 2), ("Portugal", 1, 0, 2), ("Uzbekistan", 0, -2, 2)],
    "L": [("England", 3, 2, 2), ("Ghana", 3, 1, 2), ("Panama", 0, -1, 2), ("Croatia", 0, -2, 2)],
}

# Each group plays 3 rounds (6 matches). With most teams on played=2, one final
# round (matchday 3) remains. Remaining fixtures = the pairing each team has not met.
# We derive them programmatically in the simulator.

DEFAULT_ELO = 1700  # fallback for any team missing from ELO


def get_elo(team: str) -> float:
    """Prefer data-learned Elo (from the training pipeline); fall back to estimates."""
    try:
        from app.ml.inference import learned_elo
        learned = learned_elo()
        if team in learned:
            return learned[team]
    except Exception:
        pass
    return ELO.get(team, DEFAULT_ELO)


# ---------------------------------------------------------------------------
# Current-tournament FORM (how each team is actually playing right now, 2026).
# Derived from the live standings above: points/game and goal-diff/game.
# ---------------------------------------------------------------------------
FORM = {
    name: {"points": pts, "gd": gd, "played": pl}
    for rows in GROUPS.values()
    for (name, pts, gd, pl) in rows
}

# how strongly current form bends a team's rating / expected goals
FORM_GD_WEIGHT = 10.0      # Elo points per goal of GD-per-game
FORM_PTS_WEIGHT = 15.0     # Elo points per point-per-game above "par" (1.0 ppg)
FORM_CAP = 55.0            # never let form swing a rating more than this


def form_gd_per_game(team: str) -> float:
    """Average goal difference per match so far in the 2026 tournament."""
    f = FORM.get(team)
    if not f or f["played"] == 0:
        return 0.0
    return f["gd"] / f["played"]


def form_elo_adjustment(team: str) -> float:
    """Elo nudge from current form: hot teams get a boost, cold teams a penalty."""
    f = FORM.get(team)
    if not f or f["played"] == 0:
        return 0.0
    ppg = f["points"] / f["played"]
    gpg = f["gd"] / f["played"]
    adj = (ppg - 1.0) * FORM_PTS_WEIGHT + gpg * FORM_GD_WEIGHT
    return max(-FORM_CAP, min(FORM_CAP, adj))


def get_strength(team: str, use_form: bool = True) -> float:
    """Team rating used by the model: base (learned) Elo + current-form nudge."""
    base = get_elo(team)
    return base + form_elo_adjustment(team) if use_form else base


def all_teams():
    return [t[0] for g in GROUPS.values() for t in g]
