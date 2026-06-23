"""
Create tables and load the real 2026 teams + live standings into the database.

Run:  python -m app.db.load      (from the backend/ directory)
Respects DATABASE_URL (Postgres) or defaults to SQLite.
"""
from app.db.database import engine, SessionLocal, Base
from app.db.models import Team, Standing
from app.core.data_2026 import GROUPS, get_elo


def load():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        for group, rows in GROUPS.items():
            for (name, points, gd, played) in rows:
                team = Team(name=name, elo=float(get_elo(name)), group=group)
                team.standing = Standing(points=points, goal_diff=gd, played=played)
                db.add(team)
        db.commit()
        n = db.query(Team).count()
        print(f"Loaded {n} teams with standings into the database.")
    finally:
        db.close()


if __name__ == "__main__":
    load()
