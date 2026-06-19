"""Central configuration: paths, seeds, and model hyperparameters.

All tunable knobs live here so runs are reproducible and self-documenting.
Environment variables (WC2026_*) override the defaults.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _find_repo_root() -> Path:
    """Walk upward until we find the monorepo root (contains 'artifacts')."""
    env = os.environ.get("WC2026_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "artifacts").is_dir() and (parent / "data").is_dir():
            return parent
    # Fallback: three levels up from src/wc2026/config.py -> packages/wc2026
    return here.parents[3]


REPO_ROOT = _find_repo_root()


@dataclass(frozen=True)
class Paths:
    root: Path = REPO_ROOT
    data_raw: Path = REPO_ROOT / "data" / "raw"
    data_interim: Path = REPO_ROOT / "data" / "interim"
    data_processed: Path = REPO_ROOT / "data" / "processed"
    artifacts: Path = REPO_ROOT / "artifacts"
    models: Path = REPO_ROOT / "artifacts" / "models"
    evaluations: Path = REPO_ROOT / "artifacts" / "evaluations"
    calibration: Path = REPO_ROOT / "artifacts" / "calibration"
    figures: Path = REPO_ROOT / "artifacts" / "figures"
    simulations: Path = REPO_ROOT / "artifacts" / "simulations"

    def ensure(self) -> None:
        for p in [
            self.data_raw, self.data_interim, self.data_processed,
            self.models, self.evaluations, self.calibration,
            self.figures, self.simulations,
        ]:
            p.mkdir(parents=True, exist_ok=True)


PATHS = Paths()

# Global random seed (override with WC2026_SEED)
SEED: int = int(os.environ.get("WC2026_SEED", "20260611"))

# Number of Monte Carlo simulations (override with WC2026_N_SIMS)
N_SIMS: int = int(os.environ.get("WC2026_N_SIMS", "50000"))


@dataclass(frozen=True)
class EloConfig:
    base_rating: float = 1500.0
    k_factor: float = 40.0          # base K, scaled by tournament importance
    home_advantage: float = 65.0    # Elo points, applied to non-neutral home side
    mov_enabled: bool = True        # margin-of-victory multiplier (World Football Elo)


@dataclass(frozen=True)
class DixonColesConfig:
    half_life_days: float = 730.0   # time-decay half life (~2 years)
    max_goals: int = 10             # score matrix dimension
    rho_init: float = -0.05
    ha_init: float = 0.25


@dataclass(frozen=True)
class TrainConfig:
    # Only use matches on/after this date for fitting goal models (data quality
    # of very old internationals is poor and rules differed).
    min_train_date: str = "1990-01-01"
    seed: int = SEED


# Tournament-importance weights (used by Elo K and time/quality weighting).
# Higher = more informative about true strength.
TOURNAMENT_WEIGHTS: dict[str, float] = {
    "FIFA World Cup": 1.00,
    "FIFA World Cup qualification": 0.75,
    "Copa América": 0.80,
    "UEFA Euro": 0.85,
    "UEFA Euro qualification": 0.65,
    "UEFA Nations League": 0.70,
    "African Cup of Nations": 0.75,
    "African Cup of Nations qualification": 0.55,
    "AFC Asian Cup": 0.70,
    "AFC Asian Cup qualification": 0.55,
    "Gold Cup": 0.60,
    "CONCACAF Nations League": 0.55,
    "Confederations Cup": 0.70,
    "Friendly": 0.30,
}
DEFAULT_TOURNAMENT_WEIGHT: float = 0.50


def tournament_weight(name: str) -> float:
    return TOURNAMENT_WEIGHTS.get(name, DEFAULT_TOURNAMENT_WEIGHT)
