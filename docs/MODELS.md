# IBVAP ? Model Architecture, Specifications & Licensing

This document provides a comprehensive audit of all machine learning models integrated into the Intelligent Border Video Analytics Platform (IBVAP).

---

## 1. Model Registry & Specifications

| Model | Task | Source / Reference | Code License | Weights License | Input Format | Output Format | GPU VRAM |
|---|---|---|---|---|---|---|---|
| **YOLO26m / YOLO26l** | Primary Object Detector & Tracker | [Ultralytics](https://docs.ultralytics.com/models/yolo26) | AGPL-3.0 | AGPL-3.0 / Enterprise | BGR Image (640x640) | Bounding Boxes, Class IDs, Confidence | ~111?128 MB (Shared) |
| **YOLOv8n** | Lightweight Baseline Detector | [Ultralytics](https://github.com/ultralytics/ultralytics) | AGPL-3.0 | AGPL-3.0 | BGR Image (640x640) | Bounding Boxes, Class IDs, Confidence | ~12 MB (Shared) |
| **ByteTrack** | Multi-Object Tracking & Kinematics | [FoundationVision](https://github.com/FoundationVision/ByteTrack) | MIT | N/A (Algorithmic) | Normalized Detections | Persistent Track IDs, Trajectory, Velocity | < 1 MB |
| **OSNet** | Cross-Camera Person Re-ID | [Kaiyang Zhou et al.](https://arxiv.org/abs/1905.00953) | MIT | Non-Commercial / Research | Person Crop (256x128) | L2-Normalized 512-d Feature Embedding | ~25 MB |
| **InsightFace (buffalo_l)** | Face Detection & Watchlist FRS | [DeepInsight](https://github.com/deepinsight/insightface) | MIT | Non-Commercial Research | Face / Person Crop (640x640) | 512-d ArcFace Embedding + Landmarks | ~350 MB |
| **EasyOCR / PP-OCR** | ANPR License Plate OCR | [JaidedAI](https://github.com/JaidedAI/EasyOCR) / [PaddlePaddle](https://github.com/PaddlePaddle/PaddleOCR) | Apache 2.0 | Apache 2.0 | Plate Crop (Variable) | Normalized Text String + Confidence | ~80 MB |
| **Threat Detector** | Weapon & Firearm Detection | [HuggingFace / Subh775](https://huggingface.co/Subh775/Threat-Detection-YOLOv8n) | MIT | Open Access | BGR Image (640x640) | Threat Bounding Box (Gun, Knife, Explosive) | ~35 MB |
| **LowLightProcessor** | Night Surveillance Enhancement | Retinex / CLAHE Multi-Scale | BSD-3 | N/A | BGR Image | Contrast-Enhanced BGR Image | < 5 MB |

---

## 2. Hardware Budget on NVIDIA RTX 2050 (4 GB VRAM)

* **Core Resident Models:**
  * Primary Detector (`yolo26m.pt`): **111.2 MB**
  * ByteTrack Kinematics Engine: **< 1 MB**
* **Specialist Models (Loaded on Demand):**
  * Threat Detector (`threat_detector.pt`): **~35 MB**
  * OSNet Person Re-ID (`osnet_x1_0`): **~25 MB**
  * InsightFace (`buffalo_l`): **~350 MB**
  * EasyOCR ANPR: **~80 MB**
* **Total Peak GPU Allocation across 6 concurrent CCTV streams:** **~602 MB out of 4096 MB (< 15% of total VRAM)**.

---

## 3. Licensing & Deployment Guidelines

1. **Commercial / Operational Deployment:**
   * Ultralytics YOLO models (`YOLO26`, `YOLOv8`) use the AGPL-3.0 license. Commercial deployment with closed-source modifications requires an Ultralytics enterprise license.
   * InsightFace `buffalo_l` pretrained weights are distributed for non-commercial research; for commercial deployment, replace with custom-trained ArcFace models on open datasets (e.g. MS1MV2).
   * EasyOCR and PaddleOCR are distributed under the permissive Apache-2.0 license.
   * OSNet implementation in IBVAP is clean-room PyTorch under the MIT license.
