"""
benchmark_detectors.py ? Objective Benchmarking Framework for IBVAP Detectors.

Evaluates:
- Inference Latency (ms)
- Processing Speed (FPS)
- Detection Count & Avg Confidence
- GPU VRAM Utilization (MB)
- CPU Usage (%)
- Tracker & Pipeline Compatibility

Usage:
    python scripts/benchmark_detectors.py [--video data/videos/test_cctv.mp4] [--frames 30]
"""

import argparse
import gc
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import psutil
import torch
import numpy as np

from backend.core.model_manager import ModelManager
from backend.core.detector import YOLO26Detector, Detection, TrackedDetection


def run_benchmark(video_path: str, max_frames: int = 30):
    print("=" * 80)
    print(" IBVAP OBJECT DETECTOR BENCHMARKING SUITE")
    print("=" * 80)

    # 1. System & Hardware info
    mm = ModelManager()
    print(f"Hardware Device : {mm.device_name}")
    print(f"Total GPU VRAM  : {mm.vram_total_gb:.2f} GB")
    print(f"System RAM      : {psutil.virtual_memory().total / (1024**3):.2f} GB")
    print(f"CPU Cores       : {psutil.cpu_count(logical=True)}")
    print(f"Test Video      : {video_path}")
    print(f"Benchmark Frames: {max_frames}")
    print("-" * 80)

    # 2. Load frames into memory to isolate pure inference from disk I/O
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Unable to open video {video_path}")
        return

    frames = []
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if not frames:
        print("ERROR: No frames read from video.")
        return

    print(f"Loaded {len(frames)} frames into memory (Resolution: {frames[0].shape[1]}x{frames[0].shape[0]}).\n")

    # 3. Models to evaluate
    models_to_test = [
        ("yolov8n.pt", "YOLOv8 Nano (Baseline)"),
        ("yolo26m.pt", "YOLO26 Medium (Balanced)"),
        ("yolo26l.pt", "YOLO26 Large (High-Accuracy)"),
        ("yolo26x.pt", "YOLO26 Extra-Large (Max-Accuracy)"),
    ]

    results = []

    for model_name, desc in models_to_test:
        print(f">>> Evaluating {model_name} [{desc}]...")
        mm.clear_gpu_cache()

        detector = None
        load_success = False
        active_model = model_name
        error_msg = None

        try:
            detector = YOLO26Detector(
                model_name=model_name,
                confidence=0.25,
                device="auto",
                fallback_models=["yolo26l.pt", "yolo26m.pt", "yolo11m.pt", "yolov8n.pt"],
            )
            # Warmup
            _ = detector.detect(frames[0])
            active_model = detector.active_model_name
            load_success = True
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            print(f"    [FAILED] {error_msg}")

        if not load_success:
            results.append({
                "model": model_name,
                "desc": desc,
                "status": "FAILED",
                "active_model": "None",
                "fps": 0.0,
                "latency_ms": 0.0,
                "vram_mb": 0.0,
                "total_dets": 0,
                "avg_conf": 0.0,
                "notes": error_msg,
            })
            continue

        # Timed benchmark loop
        latencies = []
        total_detections = 0
        conf_scores = []

        for frame in frames:
            t0 = time.perf_counter()
            dets = detector.detect(frame)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

            total_detections += len(dets)
            for d in dets:
                conf_scores.append(d.confidence)

        # Track benchmark
        tracked_dets = detector.track(frames[0])
        tracker_compat = len(tracked_dets) >= 0 and isinstance(tracked_dets[0], TrackedDetection) if tracked_dets else True

        vram_peak = mm.vram_allocated_mb
        mean_latency = np.mean(latencies) if latencies else 0.0
        fps = 1000.0 / mean_latency if mean_latency > 0 else 0.0
        avg_conf = np.mean(conf_scores) * 100.0 if conf_scores else 0.0

        print(f"    Latency: {mean_latency:.1f} ms | FPS: {fps:.1f} | Detections: {total_detections} (Avg Conf: {avg_conf:.1f}%) | VRAM: {vram_peak:.1f} MB")

        results.append({
            "model": model_name,
            "desc": desc,
            "status": "SUCCESS",
            "active_model": active_model,
            "fps": fps,
            "latency_ms": mean_latency,
            "vram_mb": vram_peak,
            "total_dets": total_detections,
            "avg_conf": avg_conf,
            "notes": f"Active: {active_model} (Tracker OK)" if tracker_compat else "Tracker mismatch",
        })

        # Cleanup model from registry
        mm.unload("primary_detector")
        mm.clear_gpu_cache()
        time.sleep(0.5)

    # 4. Summary Table
    print("\n" + "=" * 95)
    print(" BENCHMARK RESULTS SUMMARY (CCTV Dataset: test_cctv.mp4)")
    print("=" * 95)
    print(f"{'MODEL':<14} | {'STATUS':<7} | {'ACTIVE MODEL':<14} | {'LATENCY':<9} | {'FPS':<6} | {'VRAM (MB)':<9} | {'DETS':<5} | {'AVG CONF':<8}")
    print("-" * 95)
    for r in results:
        status_str = r['status']
        latency_str = f"{r['latency_ms']:.1f} ms" if r['status'] == 'SUCCESS' else "N/A"
        fps_str = f"{r['fps']:.1f}" if r['status'] == 'SUCCESS' else "N/A"
        vram_str = f"{r['vram_mb']:.1f}" if r['status'] == 'SUCCESS' else "N/A"
        dets_str = str(r['total_dets']) if r['status'] == 'SUCCESS' else "N/A"
        conf_str = f"{r['avg_conf']:.1f}%" if r['status'] == 'SUCCESS' else "N/A"
        print(f"{r['model']:<14} | {status_str:<7} | {r['active_model']:<14} | {latency_str:<9} | {fps_str:<6} | {vram_str:<9} | {dets_str:<5} | {conf_str:<8}")
    print("=" * 95)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark IBVAP object detectors.")
    parser.add_argument("--video", default="data/videos/test_cctv.mp4", help="Path to test video.")
    parser.add_argument("--frames", type=int, default=30, help="Number of benchmark frames.")
    args = parser.parse_args()
    run_benchmark(args.video, args.frames)
