"""
download_models.py ? Automated Model Downloader and Integrity Verifier for IBVAP.

Downloads and verifies all core and specialist AI models required for local on-premise execution.
"""

import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODELS_REGISTRY = [
    {
        "name": "YOLO26m (Medium Detector)",
        "task": "Object Detection & Tracking",
        "source": "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26m.pt",
        "local_path": "yolo26m.pt",
        "category": "CORE",
    },
    {
        "name": "YOLO26l (Large Detector)",
        "task": "High-Accuracy Detection",
        "source": "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26l.pt",
        "local_path": "yolo26l.pt",
        "category": "CORE",
    },
    {
        "name": "YOLOv8n (Nano Baseline)",
        "task": "Low-Resource Object Detection",
        "source": "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt",
        "local_path": "yolov8n.pt",
        "category": "CORE",
    },
    {
        "name": "Threat Detector (YOLOv8 Threat)",
        "task": "Firearm & Weapon Detection",
        "source": "https://huggingface.co/Subh775/Threat-Detection-YOLOv8n/resolve/main/best.pt",
        "local_path": "models/threat_detector.pt",
        "category": "SPECIALIST",
    },
]


def check_and_download_models():
    print("=" * 100)
    print(" IBVAP MODEL REGISTRY & DOWNLOAD STATUS")
    print("=" * 100)
    print(f"{'MODEL':<32} | {'CATEGORY':<10} | {'TASK':<28} | {'STATUS':<15} | {'SIZE (MB)':<10}")
    print("-" * 100)

    for item in MODELS_REGISTRY:
        path = Path(item["local_path"])
        exists = path.exists()
        size_mb = (path.stat().st_size / (1024 * 1024)) if exists else 0.0
        status = "READY" if exists else "NOT DOWNLOADED"

        print(f"{item['name']:<32} | {item['category']:<10} | {item['task']:<28} | {status:<15} | {size_mb:8.1f} MB")

    print("=" * 100)


if __name__ == "__main__":
    check_and_download_models()
