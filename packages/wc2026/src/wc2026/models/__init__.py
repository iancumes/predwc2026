"""Prediction models with a shared interface."""
from wc2026.models.base import MatchModel, market_probabilities, probs_from_matrix
from wc2026.models.boosting import BoostingModel
from wc2026.models.calibration import CalibratedModel
from wc2026.models.dixon_coles import DixonColesModel
from wc2026.models.elo import EloModel
from wc2026.models.ensemble import EnsembleModel
from wc2026.models.poisson import PoissonModel

REGISTRY: dict[str, type[MatchModel]] = {
    "elo": EloModel,
    "poisson": PoissonModel,
    "dixon_coles": DixonColesModel,
    "boosting": BoostingModel,
}

__all__ = [
    "MatchModel", "EloModel", "PoissonModel", "DixonColesModel",
    "BoostingModel", "EnsembleModel", "CalibratedModel",
    "market_probabilities", "probs_from_matrix", "REGISTRY",
]
