# YuNet face detector

`face_detection_yunet_2023mar.onnx` from [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet).
License: MIT (OpenCV Zoo). Size: 232,589 bytes.
SHA256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
Used for face visibility checks for Camera Lock.

# YOLO face detector (anime-capable)

`face_yolov8m.onnx` — ONNX export of `face_yolov8m.pt` from [Bingsu/adetailer](https://huggingface.co/Bingsu/adetailer) on Hugging Face (repo revision `53cc19de382014514d9d4038601d261a7faa9b7b`).
License: Apache-2.0 (per the model card). Trained on WIDER FACE and anime face datasets; detects anime faces, unlike YuNet.
Source file: downloaded from https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt — 52,026,019 bytes, SHA256: `717923c19b3f4bbf5250b728f1fa6b2cb72a33aed1d236ea9caf0e21ad943e5f`.
Export: Ultralytics `YOLO.export(format='onnx', imgsz=640, dynamic=False, half=True)` (FP16, fixed 640x640 input, no embedded NMS — NMS runs in the checker via OpenCV). Exported 2026-11-11.
ONNX size: 51,846,079 bytes. SHA256: `61c56e6d7c131bcfd474e6ab11b176a9e224e1ab6a837c0f47ee88c5ea5b7f7d`.
Used as the default face visibility checker for Camera Lock (bbox-based; see `application/camera/face_visibility.py`).
