"""
Inference helpers that load the trained artifacts produced by pipelines/train.py:
  - elo_ratings.json     : data-learned team strength (replaces hand estimates)
  - outcome_model.joblib : trained gradient-boosting outcome classifier

Both are loaded lazily and cached. If the artifacts are missing (training not run
yet), callers fall back to the hand-set Elo and the Poisson model.
"""
from __future__ import annotations
import json
import os
import functools

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
ELO_PATH = os.path.join(ART, "elo_ratings.json")
MODEL_PATH = os.path.join(ART, "outcome_model.joblib")

# feature order must match pipelines/train.py FEATURES
FEATURES = ["elo_diff", "elo_home", "elo_away", "neutral", "home_form", "away_form", "competitive"]


@functools.lru_cache(maxsize=1)
def learned_elo() -> dict:
    if os.path.exists(ELO_PATH):
        with open(ELO_PATH) as f:
            return json.load(f)
    return {}


@functools.lru_cache(maxsize=1)
def _model():
    if not os.path.exists(MODEL_PATH):
        return None
    import joblib
    return joblib.load(MODEL_PATH)


def has_model() -> bool:
    return _model() is not None


def predict_outcome_ml(elo_home: float, elo_away: float, neutral: bool = True) -> dict | None:
    """Return {away_win, draw, home_win} probabilities from the trained model."""
    bundle = _model()
    if bundle is None:
        return None
    model = bundle["model"]
    adv = 0 if neutral else 65.0
    # inference-time defaults: no recent-form context, treat as a competitive match
    row = [[
        (elo_home + adv) - elo_away,  # elo_diff
        elo_home, elo_away,
        1 if neutral else 0,          # neutral
        0.0, 0.0,                     # home_form, away_form (unknown at inference)
        1,                            # competitive (World Cup)
    ]]
    proba = model.predict_proba(row)[0]
    # classes are [0=away, 1=draw, 2=home]
    return {
        "away_win": round(float(proba[0]), 3),
        "draw": round(float(proba[1]), 3),
        "home_win": round(float(proba[2]), 3),
    }
