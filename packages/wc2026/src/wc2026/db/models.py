"""SQLAlchemy ORM models mirroring the documented schema.

Probabilities carry a CHECK constraint enforcing they sum to one within a
numerical tolerance; foreign keys and indices are declared where they matter.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    confederation: Mapped[str | None] = mapped_column(String(12))
    aliases: Mapped[list[TeamAlias]] = relationship(back_populates="team")


class TeamAlias(Base):
    __tablename__ = "team_aliases"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(80), index=True)
    team: Mapped[Team] = relationship(back_populates="aliases")
    __table_args__ = (UniqueConstraint("team_id", "alias"),)


class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    weight: Mapped[float] = mapped_column(Float, default=0.5)


class Match(Base):
    __tablename__ = "matches"
    match_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    home_code: Mapped[str] = mapped_column(String(48), ForeignKey("teams.code"))
    away_code: Mapped[str] = mapped_column(String(48), ForeignKey("teams.code"))
    home_team: Mapped[str] = mapped_column(String(80))
    away_team: Mapped[str] = mapped_column(String(80))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    tournament: Mapped[str] = mapped_column(String(80))
    neutral_venue: Mapped[bool] = mapped_column(default=False)
    is_world_cup: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), index=True)
    city: Mapped[str | None] = mapped_column(String(80))
    country: Mapped[str | None] = mapped_column(String(80))
    source: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (Index("ix_matches_teams", "home_code", "away_code"),)


class MatchSource(Base):
    __tablename__ = "match_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(80))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class Ranking(Base):
    __tablename__ = "rankings"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_code: Mapped[str] = mapped_column(ForeignKey("teams.code"))
    date: Mapped[date] = mapped_column(Date)
    rank: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(40))


class TeamRating(Base):
    __tablename__ = "team_ratings"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_code: Mapped[str] = mapped_column(ForeignKey("teams.code"))
    date: Mapped[date] = mapped_column(Date)
    model: Mapped[str] = mapped_column(String(40))
    rating: Mapped[float | None] = mapped_column(Float)
    attack: Mapped[float | None] = mapped_column(Float)
    defence: Mapped[float | None] = mapped_column(Float)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    data_cutoff: Mapped[date | None] = mapped_column(Date)
    calibration: Mapped[str | None] = mapped_column(String(20))
    metrics_json: Mapped[str | None] = mapped_column(String)
    weights_json: Mapped[str | None] = mapped_column(String)


class TrainingRun(Base):
    __tablename__ = "training_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_versions.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    seed: Mapped[int | None] = mapped_column(Integer)


class Prediction(Base):
    __tablename__ = "predictions"
    prediction_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    model_version_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"))
    data_cutoff: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    home_win_probability: Mapped[float] = mapped_column(Float)
    draw_probability: Mapped[float] = mapped_column(Float)
    away_win_probability: Mapped[float] = mapped_column(Float)
    expected_home_goals: Mapped[float] = mapped_column(Float)
    expected_away_goals: Mapped[float] = mapped_column(Float)
    is_frozen: Mapped[bool] = mapped_column(default=True)
    scorelines: Mapped[list[PredictionScoreline]] = relationship(back_populates="prediction")
    __table_args__ = (
        CheckConstraint(
            "abs(home_win_probability + draw_probability + away_win_probability - 1.0) < 0.001",
            name="ck_predictions_probs_sum_to_one",
        ),
        UniqueConstraint("match_id", "model_version_id", name="uq_pred_match_version"),
    )


class PredictionScoreline(Base):
    __tablename__ = "prediction_scorelines"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("predictions.prediction_id", ondelete="CASCADE")
    )
    home_goals: Mapped[int] = mapped_column(Integer)
    away_goals: Mapped[int] = mapped_column(Integer)
    probability: Mapped[float] = mapped_column(Float)
    prediction: Mapped[Prediction] = relationship(back_populates="scorelines")


class TournamentSimulation(Base):
    __tablename__ = "tournament_simulations"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    n_sims: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    model_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_versions.id"))
    results: Mapped[list[SimulationTeamResult]] = relationship(back_populates="simulation")


class SimulationTeamResult(Base):
    __tablename__ = "simulation_team_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_simulations.id", ondelete="CASCADE")
    )
    team_code: Mapped[str] = mapped_column(ForeignKey("teams.code"))
    p_win_group: Mapped[float] = mapped_column(Float)
    p_runner_up: Mapped[float] = mapped_column(Float)
    p_qualify_third: Mapped[float] = mapped_column(Float)
    p_reach_r32: Mapped[float] = mapped_column(Float)
    p_reach_r16: Mapped[float] = mapped_column(Float)
    p_reach_qf: Mapped[float] = mapped_column(Float)
    p_reach_sf: Mapped[float] = mapped_column(Float)
    p_reach_final: Mapped[float] = mapped_column(Float)
    p_champion: Mapped[float] = mapped_column(Float)
    se_champion: Mapped[float | None] = mapped_column(Float)
    simulation: Mapped[TournamentSimulation] = relationship(back_populates="results")


class DataSnapshot(Base):
    __tablename__ = "data_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    n_matches: Mapped[int] = mapped_column(Integer)
    date_min: Mapped[date | None] = mapped_column(Date)
    date_max: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String(80))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    source: Mapped[str | None] = mapped_column(String(80))
    rows_in: Mapped[int | None] = mapped_column(Integer)
    rows_out: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="ok")
