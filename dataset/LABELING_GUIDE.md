# Dataset Labeling & Custom YOLOv8 Training Guide

This guide explains how to collect images, annotate retail shelf products and empty slots, train a custom YOLOv8 model, and deploy `best.pt` into the Smart Shelf Monitoring System.

---

## 1. Directory Structure

Place your labeled dataset files inside the `dataset/` directory:

```
smart-shelf-monitor/
├── dataset/
│   ├── dataset.yaml
│   ├── LABELING_GUIDE.md
│   ├── images/
│   │   ├── train/          # 70% of images
│   │   ├── val/            # 20% of images
│   │   └── test/           # 10% of images
│   └── labels/
│       ├── train/          # Matching .txt annotation files
│       ├── val/
│       └── test/
```

Each label file must share the exact filename of its corresponding image (e.g. `shelf_001.jpg` $\rightarrow$ `shelf_001.txt`).

---

## 2. Recommended Classes in `dataset.yaml`

The predefined classes in [`dataset/dataset.yaml`](file:///d:/project/smart%20shelf/dataset/dataset.yaml) are:

```yaml
names:
  0: product
  1: bottle
  2: cup
  3: can
  4: snack_box
  5: empty_slot
```

> **Tip:** You can label products either under a generic `product` class or under specific retail item names (`bottle`, `cup`, `can`). Pre-labeling `empty_slot` allows the model to learn empty gap geometry directly in addition to the built-in occupancy fallback logic.

---

## 3. Labeling Tools

### Option A: Roboflow (Recommended - Cloud & Fast)
1. Visit [roboflow.com](https://roboflow.com) (free account).
2. Create a new Project named `smart-shelf-dataset` (Object Detection).
3. Upload your shelf images.
4. Draw bounding boxes around items and label them (`bottle`, `cup`, `empty_slot`, etc.).
5. Click **Generate Version** $\rightarrow$ Apply basic augmentations (slight brightness variation, $\pm 5^\circ$ rotation).
6. Click **Export Dataset** $\rightarrow$ Choose **YOLOv8** format $\rightarrow$ Download ZIP.
7. Unzip the downloaded `images/` and `labels/` directly into `dataset/`.

### Option B: LabelImg (Local Offline)
1. Install LabelImg:
   ```bash
   pip install labelImg
   ```
2. Launch it:
   ```bash
   labelImg
   ```
3. Set save format to **YOLO**.
4. Set Open Dir to `dataset/images/train/` and Change Save Dir to `dataset/labels/train/`.
5. Annotate rectangles and save.

---

## 4. Annotation File Format (.txt)

Each line in a YOLO label file represents one bounding box:

```
<class_id> <x_center> <y_center> <width> <height>
```
*All values are normalized between `0.0` and `1.0` relative to image dimensions.*

Example (`shelf_001.txt`):
```
1 0.2350 0.4200 0.0820 0.2850
1 0.3450 0.4180 0.0850 0.2810
5 0.4600 0.4200 0.0900 0.2800
```

---

## 5. Training the Custom Model

Run the provided helper script [`train.py`](file:///d:/project/smart%20shelf/train.py):

### On CPU (Standard PC):
```powershell
& "d:\project\venv\Scripts\python.exe" train.py --epochs 50 --batch 16 --device cpu
```

### On NVIDIA GPU (If CUDA is available):
```powershell
& "d:\project\venv\Scripts\python.exe" train.py --epochs 50 --batch 16 --device 0
```

---

## 6. Automatic Deployment of Custom Weights

When training completes:
1. `train.py` automatically copies the highest-scoring model weights (`runs/detect/.../weights/best.pt`) to:
   ```
   backend/models/best.pt
   ```
2. To activate your custom model in the live monitoring pipeline, open [`backend/.env`](file:///d:/project/smart%20shelf/backend/.env) and update:
   ```ini
   MODEL_PATH=models/best.pt
   ```
3. Restart the backend server (`run_backend.bat`). The pipeline will instantly start running inference using your newly trained custom weights!
