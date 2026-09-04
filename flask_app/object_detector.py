import cv2
from ultralytics import YOLO

class ObjectDetector:
    def __init__(self, model_path="models/coco_yolov8.pt"):
        self.model_path = model_path
        # Load YOLO model
        try:
            self.model = YOLO(self.model_path)
            print(f"Loaded YOLO model from {self.model_path}")
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            self.model = None
            
        # Store last bounding boxes per camera for smooth drawing between inferences
        self.last_boxes = {}

    def detect(self, frame, cam_id="default"):
        """
        Runs object detection on the frame and stores the results.
        """
        if self.model is None:
            return frame

        # Run inference (classes=0 for person)
        results = self.model(frame, classes=[0], verbose=False)
        
        boxes = []
        if len(results) > 0:
            for box in results[0].boxes:
                # get coordinates and confidence
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                boxes.append((x1, y1, x2, y2, conf, cls))
                
        self.last_boxes[cam_id] = boxes
        
        return self.draw_last_detections(frame, cam_id)
        
    def draw_last_detections(self, frame, cam_id="default"):
        boxes = self.last_boxes.get(cam_id, [])
        for (x1, y1, x2, y2, conf, cls) in boxes:
            # Draw green box for person
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

