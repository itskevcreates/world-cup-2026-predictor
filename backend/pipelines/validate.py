"""
Validation suite for the outcome model.

Computes, on a TIME-HELD-OUT test set (matches from 2018 onward — never seen in
training), the metrics every forecasting model should be judged on:

  * Accuracy           — fraction of correct argmax predictions (weak for 3-way football)
  * Multiclass log loss — penalises confident wrong probabilities (lower = better)
  * Brier score        — mean squared error of the probability vector (lower = better)
  * Calibration curve  — of all matches we said were ~p% home wins, did ~p% actually
                         happen? A well-calibrated model lies on the diagonal.

Backtesting against past World Cups: restrict the test set to matches with
tournament == 'FIFA World Cup' and a date in {2018, 2022} and re-run these metrics —
that measures tournament-specific skill, which is what we ultimately care about.

Run:  python backend/pipelines/validate.py
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import build_features, FEATURES, RAW  # reuse the exact feature engine
import joblib

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "ml", "artifacts")


def multiclass_brier(y_true, proba, n_classes=3):
    """Mean squared error between one-hot truth and predicted probabilities."""
    onehot = np.eye(n_classes)[y_true]
    return np.mean(np.sum((proba - onehot) ** 2, axis=1))


def calibration_table(y_true, p_home, bins=10):
    """Reliability of the home-win probability."""
    edges = np.linspace(0, 1, bins + 1)
    print("\nCalibration (home-win probability):")
    print("  predicted   observed   n")
    is_home = (y_true == 2).astype(float)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p_home >= lo) & (p_home < hi)
        if m.sum() == 0:
            continue
        print(f"  {lo:.1f}-{hi:.1f}     {is_home[m].mean():.2f}      {is_home[m].mean()*0+m.sum():.0f}")


def main():
    df = pd.read_csv(RAW, parse_dates=["date"])
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df = df.sort_values("date").reset_index(drop=True)
    feats, _ = build_features(df)
    feats = feats[feats.year >= 1990]
    test = feats[feats.year >= 2018]

    bundle = joblib.load(os.path.join(ART, "outcome_model.joblib"))
    model = bundle["model"]
    X, y = test[FEATURES].values, test["label"].values
    proba = model.predict_proba(X)

    print(f"Held-out test matches (2018+): {len(y):,}  | algorithm: {bundle.get('algorithm')}")
    print(f"Accuracy:   {accuracy_score(y, proba.argmax(1)):.3f}")
    print(f"Log loss:   {log_loss(y, proba):.3f}   (lower is better)")
    print(f"Brier:      {multiclass_brier(y, proba):.3f}   (lower is better)")

    # one-vs-rest Brier for the home-win class, plus calibration
    print(f"Brier(home): {brier_score_loss((y == 2).astype(int), proba[:, 2]):.3f}")
    calibration_table(y, proba[:, 2])

    # World Cup backtest slice
    wc = df.loc[feats.index]  # align
    print("\n(For a tournament-specific backtest, filter to tournament == 'FIFA World Cup'\n"
          " and dates 2018/2022 before scoring — same metrics, tournament-only skill.)")


if __name__ == "__main__":
    main()
