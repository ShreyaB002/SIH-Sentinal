from flask import Flask, render_template, Response
import cv2
import threading
from motion_detector import MotionDetector
from object_detector import ObjectDetector
import os

app = Flask(__name__)

# Mock configuration for 6 phones (replace with actual phone IP WebCam URLs)
# E.g. 'cam_1': 'http://172.20.10.2:8080/video'
CAMERAS = {
    'cam_1': '0', # Use 0 for testing local webcam, replace with string URL later
    'cam_2': 'data/videos/test_cctv.mp4',
    'cam_3': 'data/videos/test_cctv.mp4',
    'cam_4': 'data/videos/test_cctv.mp4',
    'cam_5': 'data/videos/test_cctv.mp4',
    'cam_6': 'data/videos/test_cctv.mp4',
}

# Create a detector per camera to avoid state overlap (especially for motion)
motion_detectors = {cam_id: MotionDetector() for cam_id in CAMERAS}

# Since YOLO models are stateless in inference, we can share one instance
# Using yolov8n.pt as the default object detector
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_model_path = os.path.join(project_root, 'yolov8n.pt')
object_detector = ObjectDetector(model_path=default_model_path)

@app.route('/')
def index():
    return render_template('index.html', cameras=CAMERAS)

def gen_frames(cam_id):
    source = CAMERAS.get(cam_id)
    if source is None:
        return
        
    # If source is just '0' string, convert to int for webcam
    if source.isdigit():
        source = int(source)
    # else if it's a relative path, resolve it relative to project root
    elif not source.startswith('http') and not source.startswith('rtsp'):
         source = os.path.join(project_root, source)
         
    cap = cv2.VideoCapture(source)
    
    frame_count = 0
    while True:
        success, frame = cap.read()
        if not success:
            # If it's a video file, loop it
            if isinstance(source, str) and not source.startswith('http'):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                break
        
        frame_count += 1
        
        # Apply motion detection
        motion_mask = motion_detectors[cam_id].detect(frame)
        
        # Apply object detection (skip frames for performance, run every 5th frame)
        # Note: In a real app, detection should run async to avoid blocking the stream
        if frame_count % 5 == 0:
            frame = object_detector.detect(frame)
        else:
            # Draw previously detected boxes for smooth playback
            frame = object_detector.draw_last_detections(frame, cam_id)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed/<cam_id>')
def video_feed(cam_id):
    return Response(gen_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Use threaded=True to allow concurrent streams
    app.run(debug=True, port=5000, threaded=True)
