"""YOLOv8 Training Helper for Smart Shelf Custom Object Detection.

Runs transfer learning on custom shelf dataset images (e.g. products, bottles, empty_slots),
and automatically exports the best weights into backend/models/best.pt.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("Error: ultralytics is not installed. Run: pip install ultralytics")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Train custom YOLOv8 model for Smart Shelf Monitoring")
    parser.add_argument(
        "--data",
        type=str,
        default="dataset/dataset.yaml",
        help="Path to dataset.yaml configuration file"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="backend/models/yolov8n.pt",
        help="Base pretrained YOLO model (e.g. yolov8n.pt, yolov8s.pt)"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs (default: 50)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Batch size (default: 16, use 8 if low GPU/RAM)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Image size in pixels (default: 640)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device to run on: 'cpu', '0', '0,1', etc."
    )
    parser.add_argument(
        "--name",
        type=str,
        default="smart_shelf_yolo",
        help="Name of the training run experiment"
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        default=True,
        help="Automatically copy trained best.pt to backend/models/best.pt"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parent

    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = project_root / data_path

    if not data_path.exists():
        alt_data = project_root / "datasets" / "dataset.yaml"
        if alt_data.exists():
            data_path = alt_data
        else:
            print(f"Error: dataset YAML not found at {data_path}. Please check path.")
            sys.exit(1)

    base_model_path = Path(args.model)
    if not base_model_path.is_absolute():
        base_model_path = project_root / base_model_path

    if not base_model_path.exists():
        base_model_str = "yolov8n.pt"
    else:
        base_model_str = str(base_model_path)

    print("=================================================================")
    print("   Smart Shelf Monitor - YOLO Model Training Utility")
    print("=================================================================")
    print(f"Dataset Config : {data_path}")
    print(f"Base Weights   : {base_model_str}")
    print(f"Epochs         : {args.epochs}")
    print(f"Batch Size     : {args.batch}")
    print(f"Image Size     : {args.imgsz}")
    print(f"Device         : {args.device}")
    print("=================================================================\n")

    print(f"Initializing YOLO model from {base_model_str}...")
    model = YOLO(base_model_str)

    print("Starting training run...")
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(project_root / "runs" / "detect"),
        name=args.name,
        exist_ok=True
    )

    print("\nTraining completed successfully!")

    # Locate output best.pt
    best_weights_path = Path(results.save_dir) / "weights" / "best.pt"
    if best_weights_path.exists() and args.deploy:
        dest_weights_path = project_root / "backend" / "models" / "best.pt"
        dest_weights_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_weights_path, dest_weights_path)
        print(f"\n[OK] Deployed trained weights to: {dest_weights_path}")
        print("To use this model in the live system, update backend/.env:")
        print("  MODEL_PATH=models/best.pt\n")


if __name__ == "__main__":
    main()
