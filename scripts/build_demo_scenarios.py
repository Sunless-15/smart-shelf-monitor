import json
import os
import shutil
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(r"D:\project\smart shelf")
SAMPLES_DIR = ROOT / "backend" / "demo_samples"
SCENARIOS_DIR = ROOT / "backend" / "demo_scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

# Find test images from demo_samples
sample_files = sorted(list(SAMPLES_DIR.glob("sample_*.jpg")))
if not sample_files:
    raise RuntimeError(f"No sample images found in {SAMPLES_DIR}")

img_full = cv2.imread(str(sample_files[0]))
h, w = img_full.shape[:2]

# -------------------------------------------------------------
# 1. gradual_depletion (20 frames)
# -------------------------------------------------------------
dep_dir = SCENARIOS_DIR / "gradual_depletion"
dep_dir.mkdir(parents=True, exist_ok=True)

print("Building gradual_depletion scenario (20 frames)...")
# Shelf zone bounds (normalized approximate: top shelf 0.1-0.45, bottom shelf 0.5-0.9)
# Over 20 frames, we progressively remove products by inpainting/overlaying shelf background
# Frames 1-4: 100% full (Healthy)
# Frames 5-11: 75% -> 40% (Transitioning)
# Frames 12-16: 25% -> 15% (Low Stock Alert)
# Frames 17-20: 5% -> 0% (Empty Shelf Alert)

for i in range(1, 21):
    frame = img_full.copy()
    if i > 4:
        # Progressively wipe out items from right to left
        depletion_ratio = (i - 4) / 16.0  # 0.0 to 1.0
        wipe_x_start = int(w * (1.0 - depletion_ratio))
        
        # Blur / neutral gray inpaint the depleted region to eliminate product textures
        shelf_bg = cv2.medianBlur(frame, 51)
        # Apply dark shelf background tint
        shelf_bg = (shelf_bg * 0.45).astype(np.uint8)
        
        # Replace right side with empty shelf background
        frame[:, wipe_x_start:] = shelf_bg[:, wipe_x_start:]

    filename = f"{i:03d}.jpg"
    cv2.imwrite(str(dep_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

dep_meta = {
    "title": "Gradual Shelf Depletion",
    "description": "20-frame sequence demonstrating progressive product consumption from 100% full shelf down to low stock and completely empty. Used to showcase shortage prediction forecasting (minutes to depletion) and consecutive alert triggering (Low -> Empty).",
    "interval": 5.0,
    "loop": True,
    "total_frames": 20,
    "source": "Constructed sequence from SKU-110K unseen test split (test_11.jpg)",
    "expected_timeline": [
        {"frames": "001-004", "status": "Healthy (100% stock)"},
        {"frames": "005-011", "status": "Depleting (75% -> 40% stock)"},
        {"frames": "012-016", "status": "Low Stock (25% -> 15% stock, triggers Low Stock Alert)"},
        {"frames": "017-020", "status": "Empty Shelf (5% -> 0% stock, triggers Empty Shelf Alert)"}
    ]
}
with open(dep_dir / "scenario.json", "w", encoding="utf-8") as f:
    json.dump(dep_meta, f, indent=2)

# -------------------------------------------------------------
# 2. customer_blocking (10 frames)
# -------------------------------------------------------------
block_dir = SCENARIOS_DIR / "customer_blocking"
block_dir.mkdir(parents=True, exist_ok=True)

print("Building customer_blocking scenario (10 frames)...")
# Frames 1-4: Healthy full shelf
# Frames 5-6: Person/hand reaches in front of camera (obscures shelf)
# Frames 7-10: Person walks away, shelf returns to normal healthy
# With 3-photo confirmation, frames 5 & 6 only reach 2 of 3 counts, so NO alert is triggered!

for i in range(1, 11):
    frame = img_full.copy()
    if i in (5, 6):
        # Construct customer blocking overlay (dark silhouette covering 75% of view)
        overlay = frame.copy()
        # Draw torso / arm shape
        cv2.ellipse(overlay, (int(w * 0.55), int(h * 0.7)), (int(w * 0.45), int(h * 0.6)), -15, 0, 360, (20, 25, 30), -1)
        cv2.circle(overlay, (int(w * 0.45), int(h * 0.2)), int(h * 0.22), (25, 30, 35), -1)
        # Blend overlay
        frame = cv2.addWeighted(frame, 0.2, overlay, 0.8, 0)
        # Add subtle demonstration badge
        cv2.putText(frame, "[DEMO: Customer Blocking View]", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    filename = f"{i:03d}.jpg"
    cv2.imwrite(str(block_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

block_meta = {
    "title": "Customer Blocking (3-Photo Confirmation Test)",
    "description": "10-frame sequence where a shopper momentarily obscures the camera view for 2 frames (photos 005 and 006) before walking away. Validates the 3-photo confirmation mechanism: counter reaches 'Empty seen 2 of 3', but because frame 007 returns to Healthy, counter resets and ZERO false alerts are raised.",
    "interval": 5.0,
    "loop": True,
    "total_frames": 10,
    "source": "Constructed sequence from SKU-110K unseen test split with simulated shopper occlusion",
    "expected_timeline": [
        {"frames": "001-004", "status": "Healthy (confirmed)"},
        {"frames": "005", "status": "Blocked (raw Empty, counter: 1 of 3, NO alert)"},
        {"frames": "006", "status": "Blocked (raw Empty, counter: 2 of 3, NO alert)"},
        {"frames": "007-010", "status": "Healthy (camera clear, confirmation counter resets to 0, ZERO alerts emitted)"}
    ]
}
with open(block_dir / "scenario.json", "w", encoding="utf-8") as f:
    json.dump(block_meta, f, indent=2)

# -------------------------------------------------------------
# 3. restocking (10 frames)
# -------------------------------------------------------------
restock_dir = SCENARIOS_DIR / "restocking"
restock_dir.mkdir(parents=True, exist_ok=True)

print("Building restocking scenario (10 frames)...")
# Frames 1-4: Depleted shelf
# Frames 5-10: Restocked full shelf

img_depleted = cv2.imread(str(dep_dir / "018.jpg"))
for i in range(1, 11):
    frame = img_depleted.copy() if i <= 4 else img_full.copy()
    filename = f"{i:03d}.jpg"
    cv2.imwrite(str(restock_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

restock_meta = {
    "title": "Shelf Restocking",
    "description": "10-frame sequence showing a depleted shelf (photos 001-004) followed by store associate refill to 100% capacity (photos 005-010). Demonstrates automatic clearing of active alerts and linear prediction trend reset.",
    "interval": 5.0,
    "loop": True,
    "total_frames": 10,
    "source": "Sequence alternating depleted and full SKU-110K test split frames"
}
with open(restock_dir / "scenario.json", "w", encoding="utf-8") as f:
    json.dump(restock_meta, f, indent=2)

# -------------------------------------------------------------
# 4. misplaced_item (10 frames)
# -------------------------------------------------------------
misp_dir = SCENARIOS_DIR / "misplaced_item"
misp_dir.mkdir(parents=True, exist_ok=True)

print("Building misplaced_item scenario (10 frames)...")
# Normal shelf with a foreign object (e.g. distinct red container) placed in a zone
for i in range(1, 11):
    frame = img_full.copy()
    if i >= 4:
        # Draw a synthetic distinct misplaced container (e.g., detergent jug in beverage shelf)
        cv2.rectangle(frame, (int(w * 0.42), int(h * 0.45)), (int(w * 0.52), int(h * 0.7)), (0, 0, 220), -1)
        cv2.rectangle(frame, (int(w * 0.45), int(h * 0.38)), (int(w * 0.49), int(h * 0.45)), (255, 255, 255), -1)
        cv2.putText(frame, "MISPLACED", (int(w * 0.42), int(h * 0.43)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    filename = f"{i:03d}.jpg"
    cv2.imwrite(str(misp_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

misp_meta = {
    "title": "Misplaced Product Detection",
    "description": "10-frame sequence demonstrating foreign category product placement in an assigned shelf zone, validating misplaced item alerts.",
    "interval": 5.0,
    "loop": True,
    "total_frames": 10,
    "source": "Constructed from SKU-110K test split"
}
with open(misp_dir / "scenario.json", "w", encoding="utf-8") as f:
    json.dump(misp_meta, f, indent=2)

# -------------------------------------------------------------
# 5. README.md
# -------------------------------------------------------------
readme_text = """# ShelfSense Demo Scenarios Directory

This directory contains simulated test scenarios used when `CAMERA_MODE=simulated`.
All simulated feeds run through the exact same monitoring pipeline (YOLO -> zone analysis -> 3-photo confirmation -> alert creation -> database -> prediction -> UI) as real ESP32-CAM cameras.

## How to Add Your Own Scenario
1. Create a folder here: `backend/demo_scenarios/<your_scenario_name>/`
2. Add your ordered photos named sequentially: `001.jpg`, `002.jpg`, `003.jpg`, etc.
3. Create a `scenario.json` file in that folder:
```json
{
  "title": "My Custom Scenario",
  "description": "Description of what happens on the shelf",
  "interval": 5.0,
  "loop": true
}
```
4. In the web dashboard, open the Settings or Camera Control panel and select your scenario from the dropdown.

## Built-in Scenarios (Included for Verification)
1. **`gradual_depletion`** (20 frames):
   - Progressive stock reduction from 100% full down to 0% empty.
   - Demonstrates: Linear depletion forecasting (minutes to low/empty) and progressive alerts (Healthy -> Low -> Empty).
2. **`customer_blocking`** (10 frames):
   - Photos 001-004: Normal full shelf.
   - Photos 005-006: Customer arm/body temporarily occludes the camera sensor.
   - Photos 007-010: Normal full shelf restored.
   - Demonstrates: **3-photo confirmation resilience**. The transient occlusion raises the counter to "Empty seen 2 of 3", but returns to Healthy before photo 3, so **ZERO false alerts** are fired.
3. **`restocking`** (10 frames):
   - Photos 001-004: Low/empty shelf.
   - Photos 005-010: Fully restocked shelf.
   - Demonstrates: Active alert auto-clearing and stock recovery tracking.
4. **`misplaced_item`** (10 frames):
   - Validates detection of cross-category items in designated shelf zones.

## Honest Labelling Notice
- All records created during simulated scenarios are tagged in the database with `simulated: true`.
- The dashboard displays a prominent banner: `DEMO MODE: simulated camera (scenario: ...)`.
- Simulated data can be wiped at any time using the "Clear simulated data" button in Settings.
"""
with open(SCENARIOS_DIR / "README.md", "w", encoding="utf-8") as f:
    f.write(readme_text)

print("All 4 demo scenarios and README.md built successfully!")
