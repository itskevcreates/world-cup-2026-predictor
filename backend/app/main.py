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
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.data_2026 import GROUPS, ELO, all_teams, get_elo
from app.ml.poisson_model import predict_match
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


@app.get("/simulate")
def simulate(n: int = Query(10000, ge=100, le=100000)):
    return run_simulations(n=n, seed=42)
