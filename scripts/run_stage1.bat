@echo off
cd /d "D:\project\smart shelf"
echo Starting Stage 1 YOLO training: %DATE% %TIME% > "D:\project\smart shelf\training_stage1.log"
"D:\project\venv\Scripts\yolo.exe" detect train data="D:\project\smart shelf\dataset_sku_subset\data.yaml" model=yolov8s.pt epochs=40 imgsz=640 batch=16 patience=10 name=sku_stage1 project="D:\project\smart shelf\runs\detect" workers=0 >> "D:\project\smart shelf\training_stage1.log" 2>&1
echo Finished Stage 1 YOLO training: %DATE% %TIME% >> "D:\project\smart shelf\training_stage1.log"
