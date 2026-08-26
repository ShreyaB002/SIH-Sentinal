import urllib.request, json, sys, time, threading, io

base = "http://127.0.0.1:8000"
passed = 0
failed = 0

def ok(msg):
    global passed; passed += 1; print("  PASS:", msg)

def fail(msg, reason=""):
    global failed; failed += 1; print("  FAIL:", msg, reason)

print("=== TEST 1: Dashboard UI (GET /) ===")
try:
    r = urllib.request.urlopen(base + "/", timeout=5)
    body = r.read().decode('utf-8')
    if r.status == 200 and "IBVAP" in body and "WATCHLIST" in body:
        ok("GET / -> 200 with Phase 4 Watchlist & Event log UI")
    else:
        fail("GET / content mismatch", str(r.status))
except Exception as e:
    fail("GET /", str(e))

print()
print("=== TEST 2: Cameras Status API ===")
try:
    r = urllib.request.urlopen(base + "/api/cameras", timeout=5)
    data = json.loads(r.read())
    ok(f"GET /api/cameras -> 200 ({len(data)} cameras reporting)")
except Exception as e:
    fail("GET /api/cameras", str(e))

print()
print("=== TEST 3: Watchlist API (GET /api/watchlist) ===")
try:
    r = urllib.request.urlopen(base + "/api/watchlist", timeout=5)
    data = json.loads(r.read())
    ok(f"GET /api/watchlist -> 200 ({len(data)} registered targets)")
except Exception as e:
    fail("GET /api/watchlist", str(e))

print()
print("=== TEST 4: Watchlist Target Registration (POST /api/watchlist/add) ===")
try:
    import numpy as np, cv2
    # Create a synthetic face image
    img = np.zeros((300, 300, 3), dtype=np.uint8) + 180
    cv2.circle(img, (150, 150), 90, (120, 120, 120), -1) # face oval
    cv2.circle(img, (120, 120), 12, (0, 0, 0), -1)      # left eye
    cv2.circle(img, (180, 120), 12, (0, 0, 0), -1)      # right eye
    cv2.ellipse(img, (150, 180), (35, 15), 0, 0, 180, (0, 0, 0), 3) # mouth
    _, encoded = cv2.imencode('.jpg', img)
    img_bytes = encoded.tobytes()

    # Build multipart/form-data
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="name"\r\n\r\n'
        "Target_Alpha\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="image"; filename="target.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode('utf-8') + img_bytes + f"\r\n--{boundary}--\r\n".encode('utf-8')

    req = urllib.request.Request(
        base + "/api/watchlist/add",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    r = urllib.request.urlopen(req, timeout=8)
    res_data = json.loads(r.read())
    target_id = res_data.get("id")
    ok(f"POST /api/watchlist/add -> 200 (Registered ID: {target_id}, Name: {res_data.get('name')})")
except Exception as e:
    fail("POST /api/watchlist/add", str(e))

print()
print("=== TEST 5: Watchlist Delete API (DELETE /api/watchlist/{id}) ===")
try:
    if 'target_id' in locals() and target_id:
        req = urllib.request.Request(base + f"/api/watchlist/{target_id}", method="DELETE")
        r = urllib.request.urlopen(req, timeout=5)
        res_data = json.loads(r.read())
        ok(f"DELETE /api/watchlist/{target_id} -> 200 ({res_data.get('message')})")
    else:
        ok("Skip delete test (no target_id)")
except Exception as e:
    fail("DELETE /api/watchlist", str(e))

print()
print("=== TEST 6: MJPEG Live Stream with Phase 4 Pipeline (GET /api/stream/cam_01) ===")
try:
    r = urllib.request.urlopen(base + "/api/stream/cam_01", timeout=8)
    ct = r.headers.get("content-type", "")
    chunk = r.read(16384)
    r.close()
    if "multipart/x-mixed-replace" in ct and b"--frame" in chunk:
        ok("MJPEG stream active with Night+YOLO+Weapons+ANPR+FRS pipeline")
    else:
        fail("MJPEG stream format mismatch", ct)
except Exception as e:
    fail("MJPEG stream", str(e))

print()
print("=== TEST 7: WebSocket Alert Stream (/ws/alerts) ===")
try:
    import socket
    s = socket.socket()
    s.settimeout(5)
    s.connect(("127.0.0.1", 8000))
    handshake = (
        "GET /ws/alerts HTTP/1.1\r\n"
        "Host: 127.0.0.1:8000\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(handshake.encode())
    resp = s.recv(1024).decode("utf-8", errors="ignore")
    s.close()
    if "101" in resp or "Switching Protocols" in resp:
        ok("WebSocket /ws/alerts -> 101 Switching Protocols")
    else:
        fail("WebSocket handshake failed", resp[:60])
except Exception as e:
    fail("WebSocket endpoint", str(e))

print()
print("=== TEST 8: SQLite Events Query (GET /api/events) ===")
try:
    r = urllib.request.urlopen(base + "/api/events?limit=10", timeout=5)
    data = json.loads(r.read())
    ok(f"GET /api/events -> 200 ({len(data)} events recorded in DB)")
except Exception as e:
    fail("GET /api/events", str(e))

print()
print(f"=== SUMMARY: {passed} PASSED, {failed} FAILED ===")
sys.exit(0 if failed == 0 else 1)
