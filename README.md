# FIFA World Cup 2026 Prediction Platform

An AI-powered platform that predicts **FIFA World Cup 2026** (USA · Mexico · Canada)
outcomes — match results, scorelines, knockout qualification, and the tournament
winner — using a Poisson/Elo prediction model and a Monte Carlo simulation engine.

Built on **real, live tournament data** (group compositions + standings as of
June 23, 2026, while the group stage is in progress).

## What it does
- **Match predictor** — win/draw/loss probabilities + most likely scorelines for any
  of the 48 teams, from an Elo → expected-goals → Poisson scoreline model.
- **Monte Carlo simulator** — finishes the remaining group games, builds the Round of
  32 (top 2 per group + 8 best third-placed, the real 2026 format), and plays the
  knockout bracket 10,000+ times to estimate each team's title chance.
- **Live standings** — current points/goal-difference for all 12 groups.

## Tech Stack
- **Backend / API:** Python, FastAPI
- **Modelling & Simulation:** Poisson scoreline model, Elo ratings, Monte Carlo
- **Frontend:** single-page dashboard (HTML/JS) calling the API
- **Trained ML:** scikit-learn (LogisticRegression + HistGradientBoosting) on 49k real matches
- **Database:** SQLAlchemy (PostgreSQL-ready, SQLite by default)
- **Frontend:** Next.js 14 + TypeScript + Tailwind (`frontend-next/`), plus a zero-build
  HTML dashboard (`frontend/index.html`)

## Project layout
```
backend/
  app/
    core/data_2026.py          # real groups, standings, team Elo ratings
    ml/poisson_model.py        # Elo -> expected goals -> scoreline probabilities
    ml/inference.py            # loads trained model + learned Elo
    ml/artifacts/              # outcome_model.joblib, elo_ratings.json (generated)
    simulation/monte_carlo.py  # tournament simulation engine
    db/database.py, models.py, load.py   # SQLAlchemy persistence
    main.py                    # FastAPI app (endpoints)
  pipelines/train.py           # trains models on historical results
  data/raw/results.csv         # 49k historical matches (downloaded)
  requirements.txt
frontend/index.html            # zero-build dashboard
frontend-next/                 # Next.js + TS + Tailwind app
```

## Run it locally
```bash
source .venv/bin/activate
pip install -r backend/requirements.txt

# (optional) train the ML models on historical data -> writes app/ml/artifacts/
python backend/pipelines/train.py

# (optional) load real teams/standings into the database
cd backend && python -m app.db.load

# start the API
uvicorn app.main:app --reload        # http://127.0.0.1:8000  (docs at /docs)

# frontend — pick one:
open frontend/index.html             # zero-build dashboard
# or the Next.js app:
cd frontend-next && npm install && npm run dev   # http://localhost:3000
```

## API endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | health check |
| GET | `/teams` | all 48 teams + (learned) Elo, strongest first |
| GET | `/groups` | live group standings |
| GET | `/db/standings` | standings read from the database |
| GET | `/power` | dynamic power ratings (power/attack/defense/momentum/SOS), all teams |
| GET | `/power?team=USA` | one team's full rating breakdown + components |
| GET | `/predict?home=Germany&away=Argentina&rating=power` | match prediction (power rating, default; `rating=elo` for the prior) |
| GET | `/predict_ml?home=Spain&away=Brazil` | trained gradient-boosting outcome odds (feeds real form) |
| GET | `/simulate?n=100000` | Monte Carlo (tournament-first), round-by-round odds |
| POST | `/parlay` | joint probability that several legs all hit (correlation-aware) |

### Parlay simulator
`POST /parlay` with legs like `{"team":"France","market":"title"}` (markets:
`advance, r16, quarter, semi, final, title`). It runs 50k tournament simulations and
returns the **joint** probability all legs hit plus fair decimal/American odds —
computed from the simulation, so correlated legs (same team or bracket path) are priced
correctly instead of a naive multiply. Available in the dashboard as the Parlay Simulator.

## Dynamic power rating
The headline rating blends **squad talent (25%) + Elo (20%) + recent form (15%) +
historical pedigree (10%)** with a deliberately down-weighted **tournament term (30%)**,
plus two corrections: a **multiplicative opponent-quality discount** (beating weak groups
counts for far less) and an **injury/availability** adjustment (e.g. Spain without Lamine
Yamal). This removes the reputation bias *and* the soft-schedule bias — current order:
**France, Argentina, Spain, Brazil, Germany**, with hosts USA/Mexico mid-pack and no
runaway favourite (France ~15%). Full formulas, the bias math, and validation are in
[backend/docs/MODEL.md](backend/docs/MODEL.md).

```bash
python backend/pipelines/validate.py   # log loss, Brier, accuracy, calibration curve
```

## Current form
Predictions blend each team's **base (learned) Elo** with how they're *actually
playing in the 2026 tournament* — points-per-game and goal-difference-per-game from
the live standings nudge the rating (capped at ±55 Elo), and the real goal-diff/game
is fed into the trained model's form features. Add `use_form=false` to `/predict` to
see the base-Elo number. `/teams` shows `elo`, `form_adj`, and combined `strength`.

## Docker
```bash
docker compose up --build
# frontend  http://localhost:3000
# API       http://localhost:8000/docs
# Postgres  localhost:5432  (user/pass/db = worldcup)
```
The backend image runs on Python 3.12 with `libgomp1`, so **XGBoost** trains and is
selected automatically if it beats HistGradientBoosting (log loss). The Next.js
frontend is multi-stage built and served. Compose also loads the real teams/standings
into Postgres on startup.

## Model performance (time-based split, test = 2018+)
| Model | Accuracy | Log loss |
|-------|----------|----------|
| Baseline (most common class) | 0.478 | – |
| LogisticRegression | 0.600 | 0.871 |
| HistGradientBoosting | 0.602 | 0.873 |

## Notes & honesty
- Elo ratings are reasoned estimates, not official figures — they drive the model and
  can be refined.
- The knockout bracket is seeded by shuffling the 32 qualifiers (a simplification of
  the exact official R32 mapping); title odds still reflect team strength.
- Next steps: persist data in PostgreSQL, train gradient-boosted models (XGBoost/
  LightGBM/CatBoost) on historical results, and rebuild the UI in Next.js.

## Status
🟢 Working vertical slice — real data → model → simulation → API → dashboard.
