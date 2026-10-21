# YOLO Training Results Report

## Two-Stage Training Architecture Rationale
Why two stages?
> **Architectural Decision**: The SKU-110K retail dataset has only a single class (`product`) and contains no annotations for empty shelf spaces. In SKU-110K, shelf gaps, out-of-stock areas, and empty rack slots are treated strictly as negative background. 
> 
> If we were to train directly or mix SKU-110K with custom shelf data that annotates `empty_slot`, the conflicting negative background labels in SKU-110K would penalize the model for detecting empty spaces and teach it that shelf gaps are not `empty_slot`.
> 
> Therefore, we train in **two stages**:
> 1. **Stage 1 (Pre-training on SKU-110K)**: Teach the network general product feature representations across thousands of dense retail items, packages, bottles, boxes, and shelf perspectives.
> 2. **Stage 2 (Fine-tuning on Custom Shelf Data)**: Fine-tune the pre-trained weights (`sku_stage1/weights/best.pt`) on custom shelf imagery with two explicit classes (`0: product`, `1: empty_slot`), calibrating the detector to discern occupied slots vs. empty shelf slots.

---

## Stage 1: Product Detection Pre-training (SKU-110K Subset)

> [!NOTE]
> **Stage 1 dataset notice**: The numbers below are measured on the SKU-110K validation subset. They represent general retail item detection across dense supermarket shelves and are not yet representative of custom store shelf geometry.

### 1. Training Setup & Hardware Configuration
- **Hardware**: NVIDIA GeForce RTX 4060 Laptop GPU (8,188 MiB VRAM), Driver 617.14
- **Environment**: Python 3.14.7, PyTorch 2.14.1+cu126, CUDA:0, Ultralytics 8.4.161
- **Base Architecture**: YOLOv8s (`yolov8s.pt`, 11.2M parameters, 28.4 GFLOPs)
- **Dataset**: `dataset_sku_subset`
  - **Train**: 1,500 images (220,632 product instances)
  - **Validation**: 300 images (45,860 product instances)
  - **Class**: `0: product`
- **Training Command**:
  ```bash
  yolo detect train data="D:/project/smart shelf/dataset_sku_subset/data.yaml" model=yolov8s.pt epochs=40 imgsz=640 batch=16 patience=10 name=sku_stage1 project="D:/project/smart shelf/runs/detect" workers=0
  ```
- **Total Training Duration**: 4,017.7 seconds (1.116 hours / ~67 minutes)
- **Peak Memory**: ~7.8 – 8.3 GB VRAM during initial mosaic epochs; ~5.0 GB during closing epochs.
- **Inference Speed**: **4.9 ms inference per image** (~154 FPS on RTX 4060)

### 2. Final Measured Metrics (Epoch 40 / 40 on Validation Subset)
All metrics reported below are real, measured numbers extracted directly from `runs/detect/sku_stage1/results.csv` and validation output:

| Metric | Measured Value | Percentage |
|---|---|---|
| **Precision (P)** | `0.90921` | **90.92%** |
| **Recall (R)** | `0.84901` | **84.90%** |
| **mAP@50** | `0.91047` | **91.05%** |
| **mAP@50-95** | `0.55358` | **55.36%** |
| **Final Train Box Loss** | `1.29162` | — |
| **Final Train Cls Loss** | `0.55142` | — |
| **Final Train DFL Loss** | `0.96074` | — |
| **Final Val Box Loss** | `1.33579` | — |
| **Final Val Cls Loss** | `0.56250` | — |
| **Final Val DFL Loss** | `0.96861` | — |

### 3. Metric Progression Across Key Epochs

| Epoch | Train Box Loss | Train Cls Loss | Precision | Recall | mAP@50 | mAP@50-95 | Cumulative Time |
|---|---|---|---|---|---|---|---|
| **1** | 1.8691 | 1.2566 | 79.41% | 70.31% | 77.24% | 42.11% | 1.8 min |
| **5** | 1.5166 | 0.7375 | 85.86% | 78.34% | 85.42% | 48.48% | 8.2 min |
| **10** | 1.4834 | 0.7052 | 87.25% | 79.22% | 87.13% | 50.44% | 16.2 min |
| **15** | 1.4258 | 0.6608 | 88.45% | 80.87% | 87.31% | 51.43% | 24.2 min |
| **20** | 1.4122 | 0.6402 | 89.19% | 82.62% | 89.28% | 53.17% | 32.4 min |
| **25** | 1.3828 | 0.6149 | 89.65% | 83.46% | 89.81% | 53.81% | 42.5 min |
| **30** | 1.3629 | 0.6004 | 89.96% | 84.36% | 90.22% | 54.41% | 51.8 min |
| **35** | 1.3133 | 0.5734 | 90.00% | 84.53% | 90.65% | 54.69% | 59.4 min |
| **40 (Final)** | **1.2916** | **0.5514** | **90.92%** | **84.90%** | **91.05%** | **55.36%** | **67.0 min** |

### 4. Generated Artifacts
- **Best Weights**: [`runs/detect/sku_stage1/weights/best.pt`](file:///D:/project/smart%20shelf/runs/detect/sku_stage1/weights/best.pt) (22.5 MB)
- **Last Weights**: [`runs/detect/sku_stage1/weights/last.pt`](file:///D:/project/smart%20shelf/runs/detect/sku_stage1/weights/last.pt) (22.5 MB)
- **Metrics Curves**:
  - Results Summary: [`runs/detect/sku_stage1/results.png`](file:///D:/project/smart%20shelf/runs/detect/sku_stage1/results.png)
  - Precision-Recall Curve: [`runs/detect/sku_stage1/BoxPR_curve.png`](file:///D:/project/smart%20shelf/runs/detect/sku_stage1/BoxPR_curve.png)
  - F1 Score Curve: [`runs/detect/sku_stage1/BoxF1_curve.png`](file:///D:/project/smart%20shelf/runs/detect/sku_stage1/BoxF1_curve.png)
  - Confusion Matrix: [`runs/detect/sku_stage1/confusion_matrix.png`](file:///D:/project/smart%20shelf/runs/detect/sku_stage1/confusion_matrix.png)

---

## Stage 2: Shelf Fine-Tuning (Classes: `product`, `empty_slot`)

> [!WARNING]
> **Status**: Paused — Waiting for user labeled dataset.
> 
> As mandated by Step 3, because custom labeled shelf images have not yet been provided, training is stopped after Stage 1. No synthetic, fabricated, or pseudo-labels will be generated.
>
> Once the custom labeled images are placed in `dataset/`, Stage 2 training can be triggered immediately using the Stage 1 checkpoint:
> ```bash
> yolo detect train data=dataset/data.yaml model=runs/detect/sku_stage1/weights/best.pt epochs=60 imgsz=640 batch=16 patience=15 name=shelf_v1
> ```
