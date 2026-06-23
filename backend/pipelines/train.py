"""
Training pipeline: learn match-outcome models from 150+ years of real
international results (martj42 dataset, backend/data/raw/results.csv).

Steps
-----
1. Load & clean the raw results.
2. Roll a chronological Elo engine through every match, recording the PRE-match
   Elo of both teams (these are leak-free features — known before kickoff).
3. Add rolling recent-form features (goal diff over each team's last 5 games).
4. Label each match: 0 = away win, 1 = draw, 2 = home win.
5. Time-based split (train < 2018, test >= 2018) so we never test on the past.
6. Train a logistic-regression baseline and a HistGradientBoosting model.
7. Report accuracy + log loss, and persist:
     - the gradient-boosting model      -> backend/app/ml/artifacts/outcome_model.joblib
     - final (latest) Elo per team       -> backend/app/ml/artifacts/elo_ratings.json

Run:  python backend/pipelines/train.py     (from the project root)
"""
from __future__ import annotations
import json
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss
import joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # project root
RAW = os.path.join(ROOT, "backend", "data", "raw", "results.csv")
ART = os.path.join(ROOT, "backend", "app", "ml", "artifacts")
os.makedirs(ART, exist_ok=True)

# --- Elo parameters (standard World-Football-Elo settings) -------------------
ELO_START = 1500.0
K = 30.0
HOME_ADV = 65.0     # Elo points of home advantage (ignored on neutral grounds)
FEATURES = ["elo_diff", "elo_home", "elo_away", "neutral", "home_form", "away_form", "competitive"]


def expected_score(elo_a, elo_b):
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def mov_multiplier(goal_diff, elo_diff):
    """Margin-of-victory multiplier: bigger wins move Elo more (dampened for blowouts)."""
    gd = max(abs(goal_diff), 1)
    return np.log(gd + 1) * (2.2 / ((elo_diff * 0.001) + 2.2))


def build_features(df: pd.DataFrame):
    elo = defaultdict(lambda: ELO_START)
    form = defaultdict(lambda: deque(maxlen=5))   # recent goal differences
    rows = []

    for r in df.itertuples(index=False):
        h, a = r.home_team, r.away_team
        neutral = 1 if r.neutral else 0
        eh, ea = elo[h], elo[a]
        adv = 0 if neutral else HOME_ADV

        hf = np.mean(form[h]) if form[h] else 0.0
        af = np.mean(form[a]) if form[a] else 0.0
        competitive = 0 if r.tournament == "Friendly" else 1

        # label from real score
        if r.home_score > r.away_score:
            label = 2
        elif r.home_score == r.away_score:
            label = 1
        else:
            label = 0

        rows.append({
            "elo_diff": (eh + adv) - ea,
            "elo_home": eh, "elo_away": ea,
            "neutral": neutral, "home_form": hf, "away_form": af,
            "competitive": competitive, "label": label, "year": r.date.year,
        })

        # --- update Elo after the match ---
        exp_h = expected_score(eh + adv, ea)
        score_h = 1.0 if label == 2 else (0.5 if label == 1 else 0.0)
        mult = mov_multiplier(r.home_score - r.away_score, abs((eh + adv) - ea))
        delta = K * mult * (score_h - exp_h)
        elo[h] += delta
        elo[a] -= delta

        form[h].append(r.home_score - r.away_score)
        form[a].append(r.away_score - r.home_score)

    return pd.DataFrame(rows), dict(elo)


def main():
    print("Loading", RAW)
    df = pd.read_csv(RAW, parse_dates=["date"])
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df = df.sort_values("date").reset_index(drop=True)
    print(f"  {len(df):,} matches, {df.date.dt.year.min()}–{df.date.dt.year.max()}")

    feats, final_elo = build_features(df)

    # train only on the modern era for outcome modelling (more relevant)
    feats = feats[feats.year >= 1990]
    train = feats[feats.year < 2018]
    test = feats[feats.year >= 2018]
    Xtr, ytr = train[FEATURES].values, train["label"].values
    Xte, yte = test[FEATURES].values, test["label"].values
    print(f"  train {len(Xtr):,}  test {len(Xte):,}")

    # baseline: most-frequent class
    base = np.full_like(yte, np.bincount(ytr).argmax())
    print(f"\nBaseline (always predict most common): acc {accuracy_score(yte, base):.3f}")

    # logistic regression
    lr = LogisticRegression(max_iter=1000)
    lr.fit(Xtr, ytr)
    pr_lr = lr.predict_proba(Xte)
    print(f"LogisticRegression:  acc {accuracy_score(yte, pr_lr.argmax(1)):.3f}  "
          f"logloss {log_loss(yte, pr_lr):.3f}")

    # gradient boosting
    gb = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05,
                                        max_depth=6, l2_regularization=1.0)
    gb.fit(Xtr, ytr)
    pr_gb = gb.predict_proba(Xte)
    print(f"HistGradientBoosting: acc {accuracy_score(yte, pr_gb.argmax(1)):.3f}  "
          f"logloss {log_loss(yte, pr_gb):.3f}")

    # persist the better model + the learned Elo ratings
    joblib.dump({"model": gb, "features": FEATURES, "classes": [0, 1, 2]},
                os.path.join(ART, "outcome_model.joblib"))
    elo_rounded = {k: round(v, 1) for k, v in sorted(final_elo.items(), key=lambda x: -x[1])}
    with open(os.path.join(ART, "elo_ratings.json"), "w") as f:
        json.dump(elo_rounded, f, indent=2)

    print(f"\nSaved model -> {ART}/outcome_model.joblib")
    print(f"Saved {len(elo_rounded)} learned Elo ratings -> {ART}/elo_ratings.json")
    top = list(elo_rounded.items())[:10]
    print("Top 10 learned Elo:", ", ".join(f"{k} {v:.0f}" for k, v in top))


if __name__ == "__main__":
    main()
