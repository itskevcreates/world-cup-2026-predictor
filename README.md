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
- *(Planned: PostgreSQL persistence, scikit-learn/XGBoost trained models, Next.js UI)*

## Project layout
```
backend/
  app/
    core/data_2026.py         # real groups, standings, team Elo ratings
    ml/poisson_model.py       # Elo -> expected goals -> scoreline probabilities
    simulation/monte_carlo.py # tournament simulation engine
    main.py                   # FastAPI app (endpoints)
  requirements.txt
frontend/
  index.html                  # dashboard (predictor, simulator, standings)
```

## Run it locally
```bash
# 1. activate the virtual environment
source .venv/bin/activate

# 2. install backend deps
pip install -r backend/requirements.txt

# 3. start the API (from the backend/ folder)
cd backend
uvicorn app.main:app --reload
#  -> API live at http://127.0.0.1:8000   (interactive docs at /docs)

# 4. open the dashboard
#    open frontend/index.html in your browser
```

## API endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | health check |
| GET | `/teams` | all 48 teams + Elo, strongest first |
| GET | `/groups` | live group standings |
| GET | `/predict?home=Spain&away=Brazil` | single-match prediction |
| GET | `/simulate?n=10000` | Monte Carlo title odds |

## Notes & honesty
- Elo ratings are reasoned estimates, not official figures — they drive the model and
  can be refined.
- The knockout bracket is seeded by shuffling the 32 qualifiers (a simplification of
  the exact official R32 mapping); title odds still reflect team strength.
- Next steps: persist data in PostgreSQL, train gradient-boosted models (XGBoost/
  LightGBM/CatBoost) on historical results, and rebuild the UI in Next.js.

## Status
🟢 Working vertical slice — real data → model → simulation → API → dashboard.
