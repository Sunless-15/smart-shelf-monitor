# Demo Samples Gallery

This directory contains 24 curated retail shelf demonstration images used by the **ShelfSense "Try It" / Demo** page.

## Origin & Fair Evaluation Guarantee
- **Strictly from Test Split**: All images in this folder were copied directly from `datasets/SKU-110K/images/` matching the official `test.txt` split (2,936 test images).
- **Zero Training Contamination**: **None** of these images were included in `dataset_sku_subset` or seen by the neural network during training. Demonstration detections reflect honest generalization on novel real-world scenes.
- **Mix of Conditions**:
  - **Full Shelves**: High-density shelves with 140+ products.
  - **Half-Empty Shelves**: Moderate stock levels with visible gaps between rows.
  - **Low Stock / Nearly Empty**: Critically depleted shelves (20–40 products remaining) designed to demonstrate out-of-stock and low-stock alert triggers.
