"""Stock Depletion Rate and Shortage Prediction Engine.

Uses historical stock percentage time series per zone to calculate:
- Depletion rate (percent depletion per minute)
- Estimated minutes until stock falls below low threshold
- Estimated minutes until stock is completely empty
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def calculate_depletion_forecast(
    history_points: List[Dict[str, Any]],
    current_stock_percent: float,
    low_threshold: float = 0.35,
    min_points: int = 2
) -> Dict[str, Any]:
    """Calculate depletion rate and time-to-depletion using linear regression.

    Args:
        history_points: List of dicts containing 'timestamp' (seconds) and 'stock_percent' (0.0-1.0).
        current_stock_percent: Latest stock percentage (0.0 to 1.0).
        low_threshold: Low stock threshold ratio (e.g. 0.35).
        min_points: Minimum required valid historical points.

    Returns:
        Dict containing:
        - depletion_rate_per_min: float or None
        - minutes_to_low: float or None
        - minutes_to_empty: float or None
        - status: "insufficient_data" | "stable_or_increasing" | "depleting" | "empty"
        - confidence: "low" | "medium" | "high" | None
    """
    # 1. Validation & Edge Cases
    if not history_points or len(history_points) < min_points:
        return {
            "depletion_rate_per_min": None,
            "minutes_to_low": None,
            "minutes_to_empty": None,
            "status": "insufficient_data",
            "confidence": None,
            "message": "Not enough historical data points to estimate trend."
        }

    # Extract time (in minutes from first point) and stock percentages
    cleaned_points = []
    for p in history_points:
        ts = p.get("timestamp")
        sp = p.get("stock_percent")
        if ts is not None and sp is not None:
            cleaned_points.append((float(ts), float(sp)))

    if len(cleaned_points) < min_points:
        return {
            "depletion_rate_per_min": None,
            "minutes_to_low": None,
            "minutes_to_empty": None,
            "status": "insufficient_data",
            "confidence": None,
            "message": "Insufficient valid timestamped data."
        }

    cleaned_points.sort(key=lambda x: x[0])
    t0 = cleaned_points[0][0]
    total_time_span_seconds = cleaned_points[-1][0] - t0

    # If time span is too narrow (< 2 seconds), don't divide by zero or extrapolate noise
    if total_time_span_seconds < 2.0:
        return {
            "depletion_rate_per_min": None,
            "minutes_to_low": None,
            "minutes_to_empty": None,
            "status": "insufficient_data",
            "confidence": None,
            "message": "Time span too short for trend analysis."
        }

    t_mins = [(ts - t0) / 60.0 for ts, _ in cleaned_points]
    s_vals = [sp for _, sp in cleaned_points]
    n = len(t_mins)

    # 2. Linear Regression (Least Squares)
    mean_t = sum(t_mins) / n
    mean_s = sum(s_vals) / n

    numerator = sum((t_mins[i] - mean_t) * (s_vals[i] - mean_s) for i in range(n))
    denominator = sum((t_mins[i] - mean_t) ** 2 for i in range(n))

    if abs(denominator) < 1e-9:
        slope = 0.0
    else:
        slope = numerator / denominator

    # Depletion rate is negative slope (positive value indicates depletion)
    depletion_rate = -slope

    # Correlation coefficient for confidence estimation
    ss_tot = sum((s_vals[i] - mean_s) ** 2 for i in range(n))
    ss_res = sum((s_vals[i] - (mean_s + slope * (t_mins[i] - mean_t))) ** 2 for i in range(n))
    r_squared = (1.0 - (ss_res / ss_tot)) if ss_tot > 1e-9 else 1.0

    if n >= 10 and r_squared > 0.7:
        confidence = "high"
    elif n >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    # 3. Analyze Forecast
    if current_stock_percent <= 0.001:
        return {
            "depletion_rate_per_min": round(max(0.0, depletion_rate), 4),
            "minutes_to_low": 0.0,
            "minutes_to_empty": 0.0,
            "status": "empty",
            "confidence": confidence,
            "message": "Shelf is currently empty."
        }

    # If depletion rate is <= 0.0001/min, stock is steady or increasing
    if depletion_rate <= 0.0001:
        return {
            "depletion_rate_per_min": 0.0,
            "minutes_to_low": None,
            "minutes_to_empty": None,
            "status": "stable_or_increasing",
            "confidence": confidence,
            "message": "Stock level is stable or restocked."
        }

    # Stock is actively depleting
    # Time until low stock
    if current_stock_percent <= low_threshold:
        minutes_to_low = 0.0
    else:
        minutes_to_low = round((current_stock_percent - low_threshold) / depletion_rate, 1)

    # Time until empty
    minutes_to_empty = round(current_stock_percent / depletion_rate, 1)

    return {
        "depletion_rate_per_min": round(depletion_rate, 4),
        "minutes_to_low": minutes_to_low,
        "minutes_to_empty": minutes_to_empty,
        "status": "depleting",
        "confidence": confidence,
        "message": f"Stock depleting at approx {round(depletion_rate * 100, 1)}% per min."
    }
