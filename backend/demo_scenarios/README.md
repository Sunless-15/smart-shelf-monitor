# ShelfSense Demo Scenarios Directory

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
