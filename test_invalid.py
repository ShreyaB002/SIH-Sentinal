import sys, time
sys.path.insert(0, '.')

from backend.core.camera_stream import CameraStream, CameraStatus

print("=== TEST 9: Invalid source -> OFFLINE, no crash ===")
bad_stream = CameraStream(
    camera_id="test_bad",
    name="Bad Camera",
    source="data/videos/nonexistent_file.mp4",
    source_type="file",
)
bad_stream.start()

# Wait up to 3 seconds for status to settle
deadline = time.time() + 3.0
while time.time() < deadline:
    if bad_stream.status != CameraStatus.CONNECTING:
        break
    time.sleep(0.1)

status = bad_stream.status
frame = bad_stream.get_frame()
bad_stream.stop()

print("  Final Status: " + status.value)
print("  Frame: " + str(frame))

if status == CameraStatus.OFFLINE:
    print("  PASS: Bad camera reached OFFLINE without crashing")
else:
    print("  FAIL: Expected OFFLINE, got " + status.value)
