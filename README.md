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
| GET | `/predict?home=Spain&away=Brazil` | Poisson match prediction + scorelines |
| GET | `/predict_ml?home=Spain&away=Brazil` | trained gradient-boosting outcome odds |
| GET | `/simulate?n=10000` | Monte Carlo title odds |

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
