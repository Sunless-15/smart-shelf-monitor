# SKU-110K Subset Validation Report

## Overview
- **Dataset**: SKU-110K Retail Dataset (Trax Retail CVPR 2019)
- **Subset Creation Date**: 2026-10-21
- **Random Seed**: 42 (reproducible sampling)
- **Target Single Class**: `0: product`
- **Configuration File**: [`dataset_sku_subset/data.yaml`](file:///D:/project/smart shelf/dataset_sku_subset/data.yaml)

---

## 1. Source Dataset & Box Distribution Analysis
An initial scan was conducted on the full SKU-110K annotations to assess feasibility of filtering for images with 10–100 boxes:

| Split | Total Images | Images with 10–100 Boxes | Min Boxes | 10th %ile | Median Boxes | 75th %ile | Max Boxes |
|---|---|---|---|---|---|---|---|
| **train** | 8219 | 384 (4.7%) | 1 | 111 | 138 | 161 | 576 |
| **val** | 588 | 18 (3.1%) | 40 | 114 | 139 | 167 | 718 |

### Sampling Methodology Note
- **Filter Evaluation**: The full SKU-110K dataset is densely packed retail shelves where the median image contains 138 boxes. Across all 8,219 train images, only **384 images** contain between 10 and 100 boxes (well below the required 1,500 train sample size). Similarly, across 588 validation images, only **18 images** contain 10–100 boxes (below the 300 required val size).
- **Sampling Decision**: Because filtering strictly to 10–100 boxes would starve the dataset of necessary training and validation volume, **plain random sampling with seed 42** was performed across the train (8,219 images) and validation (588 images) splits, strictly excluding the test split (2,936 images).

---

## 2. Subset Split Verification

| Metric | Train Split | Validation Split | Total Subset |
|---|---|---|---|
| **Images Count** | 1500 | 300 | 1800 |
| **Labels Count** | 1500 | 300 | 1800 |
| **Missing Labels** | 0 | 0 | 0 |
| **Corrupt Images** | 0 | 0 | 0 |
| **Invalid Class IDs (non-0)** | 0 | 0 | 0 |
| **Invalid Coordinates (<0 or >1)** | 0 | 0 | 0 |
| **Total Product Bounding Boxes** | 220,632 | 45,860 | 266,492 |
| **Average Boxes per Image** | 147.1 | 152.9 | 148.1 |

---

## 3. Directory Layout
```
dataset_sku_subset/
├── data.yaml
├── images/
│   ├── train/ (1,500 images)
│   └── val/   (300 images)
└── labels/
    ├── train/ (1,500 label files)
    └── val/   (300 label files)
```

## 4. Conclusion
The subset has been created, paired 1-to-1 (every image has an identical label file), fully validated for image integrity and bounding box normalcy, and is completely ready for Stage 1 training (`sku_stage1`).
