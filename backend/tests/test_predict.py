"""Unit tests for stock depletion forecast and shortage prediction."""

import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from inference.predict import calculate_depletion_forecast


def test_predict_insufficient_data():
    """Verify prediction returns None/insufficient_data when points are lacking."""
    # Empty list
    res_empty = calculate_depletion_forecast([], current_stock_percent=0.8)
    assert res_empty["status"] == "insufficient_data"
    assert res_empty["minutes_to_low"] is None
    assert res_empty["minutes_to_empty"] is None

    # Only 1 point
    res_one = calculate_depletion_forecast([{"timestamp": 1000.0, "stock_percent": 0.8}], 0.8)
    assert res_one["status"] == "insufficient_data"
    assert res_one["minutes_to_low"] is None

    # Points too close together (< 2s)
    res_close = calculate_depletion_forecast([
        {"timestamp": 1000.0, "stock_percent": 0.8},
        {"timestamp": 1000.5, "stock_percent": 0.7}
    ], 0.7)
    assert res_close["status"] == "insufficient_data"


def test_predict_depleting_stock():
    """Verify calculation of depletion rate, minutes to low, and minutes to empty."""
    # Simulated depletion:
    # At t=0s (0m): stock = 1.0 (100%)
    # At t=60s (1m): stock = 0.9 (90%)
    # At t=120s (2m): stock = 0.8 (80%)
    # Rate of depletion is 0.1 (10%) per minute
    # Current stock is 0.8. Low threshold is 0.3 (30%).
    # Minutes to low = (0.8 - 0.3) / 0.1 = 5.0 minutes.
    # Minutes to empty = 0.8 / 0.1 = 8.0 minutes.
    history = [
        {"timestamp": 0.0, "stock_percent": 1.0},
        {"timestamp": 60.0, "stock_percent": 0.9},
        {"timestamp": 120.0, "stock_percent": 0.8},
    ]

    res = calculate_depletion_forecast(
        history_points=history,
        current_stock_percent=0.8,
        low_threshold=0.3
    )

    assert res["status"] == "depleting"
    assert res["depletion_rate_per_min"] == pytest.approx(0.1, abs=0.01)
    assert res["minutes_to_low"] == pytest.approx(5.0, abs=0.1)
    assert res["minutes_to_empty"] == pytest.approx(8.0, abs=0.1)


def test_predict_stable_or_increasing():
    """Verify that steady or restocked shelves do not predict false shortages."""
    # Stock level constant at 0.7
    history_stable = [
        {"timestamp": 0.0, "stock_percent": 0.7},
        {"timestamp": 60.0, "stock_percent": 0.7},
        {"timestamp": 120.0, "stock_percent": 0.7},
    ]
    res_stable = calculate_depletion_forecast(history_stable, current_stock_percent=0.7)
    assert res_stable["status"] == "stable_or_increasing"
    assert res_stable["minutes_to_low"] is None
    assert res_stable["minutes_to_empty"] is None

    # Stock level increasing (restocking event)
    history_increasing = [
        {"timestamp": 0.0, "stock_percent": 0.2},
        {"timestamp": 60.0, "stock_percent": 0.5},
        {"timestamp": 120.0, "stock_percent": 0.9},
    ]
    res_inc = calculate_depletion_forecast(history_increasing, current_stock_percent=0.9)
    assert res_inc["status"] == "stable_or_increasing"
    assert res_inc["minutes_to_low"] is None


def test_predict_already_empty_or_low():
    """Verify behavior when stock is already at 0% or below low threshold."""
    history = [
        {"timestamp": 0.0, "stock_percent": 0.4},
        {"timestamp": 60.0, "stock_percent": 0.2},
    ]

    # Current stock is 0.2, low threshold is 0.35 -> already low!
    res_low = calculate_depletion_forecast(history, current_stock_percent=0.2, low_threshold=0.35)
    assert res_low["minutes_to_low"] == 0.0
    assert res_low["minutes_to_empty"] > 0

    # Current stock is 0.0 -> empty!
    res_empty = calculate_depletion_forecast(history, current_stock_percent=0.0, low_threshold=0.35)
    assert res_empty["status"] == "empty"
    assert res_empty["minutes_to_low"] == 0.0
    assert res_empty["minutes_to_empty"] == 0.0
