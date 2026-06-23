"""
FastAPI backend for the World Cup 2026 Prediction Platform.

Run from the backend/ directory:
    uvicorn app.main:app --reload

Endpoints:
    GET /                         -> health check
    GET /teams                    -> all 48 teams + Elo
    GET /groups                   -> live group standings
    GET /predict?home=&away=      -> single match prediction
    GET /simulate?n=10000         -> Monte Carlo title odds
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Team

from app.core.data_2026 import GROUPS, ELO, all_teams, get_elo
from app.ml.poisson_model import predict_match
from app.ml.inference import predict_outcome_ml, has_model
from app.simulation.monte_carlo import run_simulations

app = FastAPI(title="World Cup 2026 Prediction Platform", version="0.1.0")

# allow the frontend (any origin in dev) to call the API
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok", "tournament": "FIFA World Cup 2026", "teams": len(all_teams())}


@app.get("/teams")
def teams():
    return sorted(
        ({"team": t, "elo": get_elo(t)} for t in all_teams()),
        key=lambda x: x["elo"], reverse=True,
    )


@app.get("/groups")
def groups():
    out = {}
    for g, rows in GROUPS.items():
        out[g] = [
            {"team": n, "points": p, "goal_diff": gd, "played": pl}
            for (n, p, gd, pl) in rows
        ]
    return out


@app.get("/predict")
def predict(home: str = Query(...), away: str = Query(...)):
    if home not in ELO or away not in ELO:
        raise HTTPException(404, "Unknown team. Check /teams for valid names.")
    return predict_match(home, away).as_dict()


@app.get("/db/standings")
def db_standings(db: Session = Depends(get_db)):
    """Standings read from the database (proves the persistence layer works)."""
    teams = db.query(Team).all()
    if not teams:
        raise HTTPException(503, "Database empty. Run: python -m app.db.load")
    return sorted(
        ({"team": t.name, "group": t.group, "elo": round(t.elo, 1),
          "points": t.standing.points, "goal_diff": t.standing.goal_diff}
         for t in teams),
        key=lambda x: (x["group"], -x["points"], -x["goal_diff"]),
    )


@app.get("/predict_ml")
def predict_ml(home: str = Query(...), away: str = Query(...), neutral: bool = True):
    """Outcome probabilities from the trained gradient-boosting model."""
    if home not in ELO or away not in ELO:
        raise HTTPException(404, "Unknown team. Check /teams for valid names.")
    if not has_model():
        raise HTTPException(503, "Trained model not found. Run pipelines/train.py first.")
    probs = predict_outcome_ml(get_elo(home), get_elo(away), neutral=neutral)
    return {"home": home, "away": away, "model": "HistGradientBoosting", "probabilities": probs}


@app.get("/simulate")
def simulate(n: int = Query(10000, ge=100, le=100000)):
    return run_simulations(n=n, seed=42)
