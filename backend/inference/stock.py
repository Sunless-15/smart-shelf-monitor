"""Stock counting, zone occupancy, and misplaced item detection logic.

Processes YOLO detections against defined shelf zones, calculating stock counts,
stock percentages, state (ok, low, empty), and identifying misplaced products.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def is_point_in_zone(point: List[float], coords: Dict[str, float]) -> bool:
    """Check if normalized point (cx, cy) is inside normalized rectangle coords."""
    cx, cy = point
    x1 = coords.get("x1", 0.0)
    y1 = coords.get("y1", 0.0)
    x2 = coords.get("x2", 1.0)
    y2 = coords.get("y2", 1.0)

    # Ensure min/max ordering
    left, right = min(x1, x2), max(x1, x2)
    top, bottom = min(y1, y2), max(y1, y2)

    return (left <= cx <= right) and (top <= cy <= bottom)


def analyze_shelf_zones(
    zones: List[Dict[str, Any]], 
    detections: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Analyze stock status and misplaced items for all shelf zones.

    Args:
        zones: List of zone definitions from DB.
        detections: List of detection dictionaries from YOLODetector.

    Returns:
        List of evaluated zone status dictionaries.
    """
    evaluated_zones: List[Dict[str, Any]] = []

    for zone in zones:
        zone_id = str(zone.get("_id", zone.get("id", "")))
        zone_name = zone.get("name", "Unnamed Zone")
        expected_class = str(zone.get("expected_class", "")).lower().strip()
        full_count = max(1, int(zone.get("full_count", 5)))
        low_threshold = float(zone.get("low_threshold", 0.35))
        coords = zone.get("coords", {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0})

        matching_detections: List[Dict[str, Any]] = []
        misplaced_detections: List[Dict[str, Any]] = []

        # Categorize detections falling inside this zone
        for det in detections:
            center = det.get("center", [0.0, 0.0])
            if is_point_in_zone(center, coords):
                det_class = det.get("class_name", "").lower().strip()
                if det_class == expected_class:
                    matching_detections.append(det)
                else:
                    misplaced_detections.append(det)

        item_count = len(matching_detections)
        misplaced_count = len(misplaced_detections)
        
        # Stock percentage calculation
        stock_percent = round(min(1.0, item_count / float(full_count)), 3)

        # State determination
        # Empty space fallback: if matching item count is 0, the slot is empty
        if item_count == 0:
            state = "empty"
        elif stock_percent <= low_threshold:
            state = "low"
        else:
            state = "ok"

        evaluated_zones.append({
            "zone_id": zone_id,
            "name": zone_name,
            "expected_class": expected_class,
            "full_count": full_count,
            "low_threshold": low_threshold,
            "coords": coords,
            "current_count": item_count,
            "stock_percent": stock_percent,
            "state": state,
            "is_empty": (state == "empty"),
            "is_low": (state == "low"),
            "is_ok": (state == "ok"),
            "misplaced_count": misplaced_count,
            "misplaced_items": [
                {
                    "class_name": d.get("class_name"),
                    "confidence": d.get("confidence"),
                    "box": d.get("box"),
                    "pixel_box": d.get("pixel_box"),
                }
                for d in misplaced_detections
            ],
            "detected_items": [
                {
                    "class_name": d.get("class_name"),
                    "confidence": d.get("confidence"),
                    "box": d.get("box"),
                    "pixel_box": d.get("pixel_box"),
                }
                for d in matching_detections
            ]
        })

    return evaluated_zones


def annotate_frame(
    frame: np.ndarray, 
    zone_results: List[Dict[str, Any]], 
    detections: Optional[List[Dict[str, Any]]] = None
) -> np.ndarray:
    """Render zones, bounding boxes, labels, and misplaced warnings onto the frame.

    Colors:
    - OK: Emerald Green (50, 205, 50)
    - Low: Amber/Orange (0, 165, 255)
    - Empty: Vivid Red (0, 0, 255)
    - Misplaced: Magenta (255, 0, 255)
    """
    if frame is None or frame.size == 0:
        return frame

    annotated = frame.copy()
    h, w = annotated.shape[:2]

    STATE_COLORS = {
        "ok": (50, 205, 50),       # Green
        "low": (0, 165, 255),      # Orange/Amber
        "empty": (0, 0, 255),      # Red
    }

    # 1. Draw Shelf Zones
    for zone in zone_results:
        coords = zone.get("coords", {})
        x1 = int(coords.get("x1", 0.0) * w)
        y1 = int(coords.get("y1", 0.0) * h)
        x2 = int(coords.get("x2", 1.0) * w)
        y2 = int(coords.get("y2", 1.0) * h)

        state = zone.get("state", "ok")
        color = STATE_COLORS.get(state, (200, 200, 200))
        name = zone.get("name", "Zone")
        count = zone.get("current_count", 0)
        full = zone.get("full_count", 1)
        pct = int(zone.get("stock_percent", 0.0) * 100)
        misplaced = zone.get("misplaced_count", 0)

        # Draw transparent fill overlay for zone
        overlay = annotated.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        alpha = 0.12 if state != "empty" else 0.20
        cv2.addWeighted(overlay, alpha, annotated, 1 - alpha, 0, annotated)

        # Draw zone boundary outline (dashed/solid)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Draw zone header banner
        banner_h = 24
        cv2.rectangle(annotated, (x1, max(0, y1 - banner_h)), (min(w, x1 + 240), y1), (25, 25, 25), -1)
        cv2.rectangle(annotated, (x1, max(0, y1 - banner_h)), (min(w, x1 + 240), y1), color, 1)

        header_text = f"{name}: {count}/{full} ({pct}%) [{state.upper()}]"
        cv2.putText(
            annotated, 
            header_text, 
            (x1 + 4, max(14, y1 - 7)), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.38, 
            (255, 255, 255), 
            1, 
            cv2.LINE_AA
        )

        # If misplaced items exist, draw warning banner
        if misplaced > 0:
            warning_text = f"! MISPLACED ({misplaced}) !"
            cv2.rectangle(annotated, (x1, y2 - 20), (min(w, x1 + 140), y2), (255, 0, 255), -1)
            cv2.putText(
                annotated, 
                warning_text, 
                (x1 + 4, y2 - 6), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.36, 
                (255, 255, 255), 
                1, 
                cv2.LINE_AA
            )

    # 2. Draw Individual Detection Boxes
    for zone in zone_results:
        # Expected items
        for item in zone.get("detected_items", []):
            pb = item.get("pixel_box")
            if pb and len(pb) == 4:
                px1, py1, px2, py2 = pb
                cv2.rectangle(annotated, (px1, py1), (px2, py2), (50, 220, 50), 1)
                cv2.putText(
                    annotated, 
                    f"{item.get('class_name')} {item.get('confidence', '')}", 
                    (px1, max(12, py1 - 4)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.35, 
                    (50, 220, 50), 
                    1, 
                    cv2.LINE_AA
                )

        # Misplaced items
        for item in zone.get("misplaced_items", []):
            pb = item.get("pixel_box")
            if pb and len(pb) == 4:
                px1, py1, px2, py2 = pb
                cv2.rectangle(annotated, (px1, py1), (px2, py2), (255, 0, 255), 2)
                cv2.putText(
                    annotated, 
                    f"MISPLACED: {item.get('class_name')}", 
                    (px1, max(12, py1 - 4)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.38, 
                    (255, 0, 255), 
                    1, 
                    cv2.LINE_AA
                )

    return annotated
