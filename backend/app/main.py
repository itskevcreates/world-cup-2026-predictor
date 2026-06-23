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

from app.core.data_2026 import (
    GROUPS, ELO, all_teams, get_elo, get_strength,
    form_gd_per_game, form_elo_adjustment,
)
from app.ml.poisson_model import predict_match
from app.ml.inference import predict_outcome_ml, has_model, model_name
from app.ml.power_rating import power_ratings, power_of
from app.simulation.monte_carlo import run_simulations, run_parlay, STAGE_RANK
from pydantic import BaseModel, Field

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
        ({
            "team": t,
            "elo": round(get_elo(t), 1),
            "form_adj": round(form_elo_adjustment(t), 1),
            "strength": round(get_strength(t), 1),
        } for t in all_teams()),
        key=lambda x: x["strength"], reverse=True,
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
def predict(home: str = Query(...), away: str = Query(...),
           rating: str = Query("power", pattern="^(power|elo)$")):
    """Match prediction. rating=power (tournament-first, default) or elo (form-adjusted)."""
    if home not in ELO or away not in ELO:
        raise HTTPException(404, "Unknown team. Check /teams for valid names.")
    fn = power_of if rating == "power" else None
    out = predict_match(home, away, rating_fn=fn).as_dict()
    out["rating_system"] = rating
    return out


@app.get("/power")
def power(team: str | None = None):
    """Dynamic power ratings (tournament-first). Optionally filter to one team."""
    ratings = power_ratings()
    if team:
        if team not in ratings:
            raise HTTPException(404, "Unknown team. Check /teams for valid names.")
        r = ratings[team]
        return {
            "team": r.team, "power": r.power, "attack": r.attack, "defense": r.defense,
            "momentum": r.momentum, "schedule_strength": r.schedule_strength,
            "tournament_elo": r.tournament_elo, "components": r.components,
        }
    return sorted(
        ({"team": r.team, "power": r.power, "attack": r.attack, "defense": r.defense,
          "momentum": r.momentum, "schedule_strength": r.schedule_strength,
          "tournament_elo": r.tournament_elo} for r in ratings.values()),
        key=lambda x: x["power"], reverse=True,
    )


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
    probs = predict_outcome_ml(
        get_elo(home), get_elo(away), neutral=neutral,
        home_form=form_gd_per_game(home), away_form=form_gd_per_game(away),
    )
    return {
        "home": home, "away": away, "model": model_name(),
        "form": {home: round(form_gd_per_game(home), 2), away: round(form_gd_per_game(away), 2)},
        "probabilities": probs,
    }


@app.get("/simulate")
def simulate(n: int = Query(50000, ge=1000, le=200000)):
    """Monte Carlo tournament simulation (tournament-first power ratings)."""
    return run_simulations(n=n, seed=42)


class ParlayLeg(BaseModel):
    team: str
    market: str = Field(description="advance | r16 | quarter | semi | final | title")


class ParlayRequest(BaseModel):
    legs: list[ParlayLeg] = Field(min_length=1, max_length=10)
    n: int = Field(default=50000, ge=1000, le=200000)


@app.post("/parlay")
def parlay(req: ParlayRequest):
    """
    Joint probability that ALL legs hit, from the Monte Carlo (correlation-aware).
    Each leg: a team reaching a stage (advance/r16/quarter/semi/final/title).
    """
    for leg in req.legs:
        if leg.team not in ELO:
            raise HTTPException(404, f"Unknown team: {leg.team}")
        if leg.market not in STAGE_RANK or leg.market == "none":
            raise HTTPException(422, f"Bad market '{leg.market}'. Use advance|r16|quarter|semi|final|title")
    legs = [{"team": l.team, "market": l.market} for l in req.legs]
    return run_parlay(legs, n=req.n, seed=42)
