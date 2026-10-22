# ShelfSense: Inference Performance & Latency Benchmark

## 1. Executive Summary

This report documents the real measured object detection latency of the ShelfSense computer vision pipeline. Benchmarking was performed using our trained Stage 1 YOLOv8s detector (`sku_stage1.pt`, 22.5 MB, trained to 91.05% mAP@50 on SKU-110K) on the host system's hardware accelerator.

- **Mean End-to-End Latency**: **84.68 ms** (~**11.8 FPS**)
- **Median Latency**: **83.65 ms**
- **Min / Max Latency**: **31.92 ms** / **125.65 ms**
- **95th Percentile Latency**: **115.98 ms**
- **Consistency (Std Dev)**: ±20.59 ms
- **Test Dataset**: 20 unseen images from SKU-110K test split (`sample_01` to `sample_20`)
- **System Capture Interval**: 5.0 seconds (200 ms allocated budget; processing takes only **84.7 ms** or **1.69%** of available cycle time)

---

## 2. Hardware and Environment Specification

| Parameter | Measured Specification |
|---|---|
| **GPU Accelerator** | **NVIDIA GeForce RTX 4060 Laptop GPU** |
| **GPU Dedicated VRAM** | 8188 MiB GDDR6 |
| **CUDA Driver / Runtime** | CUDA 12.6 |
| **PyTorch Version** | 2.14.1+cu126 |
| **Ultralytics YOLO** | YOLOv8s (22,494,698 bytes) |
| **Active Model** | `sku_stage1.pt` (`sku_stage1 (trained on products)`) |
| **Inference Width** | 640 px (aspect ratio preserved) |
| **Confidence Threshold** | 0.35 |
| **IoU NMS Threshold** | 0.45 |
| **VRAM Footprint** | 42.5 MB allocated (98.0 MB reserved) |

---

## 3. Measured Per-Image Benchmark Table (20 Samples)

Each image was loaded from `backend/demo_samples/`, resized to 640px model width, passed through GPU forward inference and non-maximum suppression (NMS), and synchronized using CUDA event timing.

| # | Sample File | Original Resolution | Products Counted | Latency (ms) |
|---|---|---|---|---|
| 1 | `sample_01_test_11.jpg` | 1920x2560 | 135 | **109.93 ms** |
| 2 | `sample_02_test_40.jpg` | 1920x2560 | 147 | **62.42 ms** |
| 3 | `sample_03_test_56.jpg` | 2448x3264 | 129 | **115.47 ms** |
| 4 | `sample_04_test_159.jpg` | 2448x3264 | 97 | **78.28 ms** |
| 5 | `sample_05_test_200.jpg` | 2448x3264 | 141 | **79.15 ms** |
| 6 | `sample_06_test_203.jpg` | 2340x4160 | 141 | **102.27 ms** |
| 7 | `sample_07_test_281.jpg` | 2448x3264 | 124 | **86.91 ms** |
| 8 | `sample_08_test_311.jpg` | 2160x3840 | 93 | **125.65 ms** |
| 9 | `sample_09_test_16.jpg` | 2448x3264 | 162 | **96.97 ms** |
| 10 | `sample_10_test_64.jpg` | 1920x2560 | 117 | **59.51 ms** |
| 11 | `sample_11_test_294.jpg` | 2448x3264 | 26 | **84.58 ms** |
| 12 | `sample_12_test_864.jpg` | 3120x4160 | 61 | **93.62 ms** |
| 13 | `sample_13_test_1348.jpg` | 2448x3264 | 61 | **74.92 ms** |
| 14 | `sample_14_test_2151.jpg` | 2448x3264 | 102 | **75.74 ms** |
| 15 | `sample_15_test_2310.jpg` | 2448x3264 | 88 | **82.72 ms** |
| 16 | `sample_16_test_2866.jpg` | 4320x2432 | 84 | **94.03 ms** |
| 17 | `sample_17_test_193.jpg` | 2560x1920 | 20 | **31.92 ms** |
| 18 | `sample_18_test_228.jpg` | 2340x4160 | 144 | **95.04 ms** |
| 19 | `sample_19_test_264.jpg` | 3264x2448 | 57 | **72.60 ms** |
| 20 | `sample_20_test_974.jpg` | 3264x2448 | 63 | **71.79 ms** |

---

## 4. Key Engineering Insights

1. **Massive Headroom for Multi-Shelf Scaling**:
   - Because inference takes only **~84.7 ms** per photo, a single central store PC with an RTX 4060 can easily service **over 50 concurrent shelf cameras** reporting every 5 seconds without queuing delays.
2. **Dense Bounding Box Throughput**:
   - The model effortlessly identified dozens to hundreds of packed retail products per shelf view (up to 162 items in a single photo) in under 125.7 ms.
3. **Low VRAM Footprint**:
   - Model execution requires only **42.5 MB** of active GPU memory, leaving >7,000 MB VRAM free for operating system, web dashboard rendering, and multi-threaded background workers.
4. **Edge Feasibility**:
   - With an average latency of ~84.7 ms, the system operates comfortably well within the 5.0-second ESP32 capture interval, ensuring real-time response to stock movements.
