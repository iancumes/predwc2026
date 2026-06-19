import numpy as np

from wc2026.evaluation.metrics import (
    brier_score,
    expected_calibration_error,
    log_loss_multiclass,
    rps_score,
)


def test_log_loss_perfect_and_uniform():
    y = np.array([0, 1, 2])
    perfect = np.eye(3)[y]
    assert log_loss_multiclass(perfect, y) < 1e-6
    uniform = np.full((3, 3), 1 / 3)
    assert abs(log_loss_multiclass(uniform, y) - np.log(3)) < 1e-9


def test_brier_bounds():
    y = np.array([0, 1, 2])
    assert brier_score(np.eye(3)[y], y) < 1e-9
    # worst case: full mass on the wrong class
    worst = np.zeros((3, 3)); worst[np.arange(3), (y + 1) % 3] = 1
    assert brier_score(worst, y) == 2.0


def test_rps_orders_distance():
    # predicting away when home happens is worse than predicting draw
    y = np.array([0])
    p_draw = np.array([[0.0, 1.0, 0.0]])
    p_away = np.array([[0.0, 0.0, 1.0]])
    assert rps_score(p_away, y) > rps_score(p_draw, y)


def test_ece_zero_when_calibrated():
    rng = np.random.default_rng(0)
    # construct perfectly calibrated-ish: confidence == accuracy
    p = np.full((1000, 3), [0.8, 0.1, 0.1])
    y = np.where(rng.random(1000) < 0.8, 0, 1)
    assert expected_calibration_error(p, y) < 0.05
