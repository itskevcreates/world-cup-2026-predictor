"""SQLAlchemy ORM models for the World Cup 2026 platform."""
from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    elo: Mapped[float] = mapped_column(Float)
    group: Mapped[str] = mapped_column(String(1), index=True)

    standing: Mapped["Standing"] = relationship(back_populates="team", uselist=False)


class Standing(Base):
    __tablename__ = "standings"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), unique=True)
    points: Mapped[int] = mapped_column(Integer)
    goal_diff: Mapped[int] = mapped_column(Integer)
    played: Mapped[int] = mapped_column(Integer)

    team: Mapped["Team"] = relationship(back_populates="standing")
