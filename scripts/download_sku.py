import sys
from ultralytics.data.utils import check_det_dataset

print("Starting SKU-110K dataset check and download via Ultralytics...", flush=True)
try:
    dataset_info = check_det_dataset("SKU-110K.yaml")
    print("SKU-110K dataset check and download finished successfully!", flush=True)
    print("Dataset info:", dataset_info, flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
