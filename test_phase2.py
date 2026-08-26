import urllib.request, json, sys, time, threading

base = "http://127.0.0.1:8000"
passed = 0
failed = 0

def ok(msg):
    global passed; passed += 1; print("  PASS:", msg)

def fail(msg, reason=""):
    global failed; failed += 1; print("  FAIL:", msg, reason)

print("=== TEST 1: Server startup ===")
try:
    r = urllib.request.urlopen(base + "/", timeout=5)
    ok("GET / -> " + str(r.status))
except Exception as e:
    fail("GET /", str(e))

print()
print("=== TEST 4: Camera status API ===")
try:
    r = urllib.request.urlopen(base + "/api/cameras", timeout=5)
    data = json.loads(r.read())
    ok("GET /api/cameras -> " + str(r.status))
    for cam in data:
        print("   ", cam["id"], "->", cam["status"])
    if all(c["status"] in ("ONLINE","CONNECTING") for c in data if c["id"] != "cam_03"):
        ok("File cameras are ONLINE/CONNECTING")
    else:
        fail("Some file cameras not ONLINE")
except Exception as e:
    fail("Camera status API", str(e))

print()
print("=== TEST 5: MJPEG stream (cam_01) ===")
try:
    r = urllib.request.urlopen(base + "/api/stream/cam_01", timeout=10)
    ct = r.headers.get("content-type","")
    chunk = r.read(16384)
    r.close()
    if "multipart/x-mixed-replace" in ct and b"--frame" in chunk and b"image/jpeg" in chunk:
        ok("MJPEG stream healthy (boundary + JPEG confirmed)")
    else:
        fail("MJPEG format wrong", "ct=" + ct)
except Exception as e:
    fail("MJPEG stream", str(e))

print()
print("=== TEST (NEW): WebSocket endpoint exists ===")
try:
    import urllib.error
    # WebSocket upgrade ? check that the endpoint returns 101 or at least connects
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
        fail("WebSocket upgrade failed", resp[:80])
except Exception as e:
    fail("WebSocket endpoint", str(e))

print()
print("=== TEST (NEW): Events API ===")
try:
    r = urllib.request.urlopen(base + "/api/events?limit=10", timeout=5)
    data = json.loads(r.read())
    ok("GET /api/events -> " + str(r.status) + " (" + str(len(data)) + " events so far)")
except Exception as e:
    fail("Events API", str(e))

print()
print("=== TEST 7: Multiple simultaneous streams ===")
results = {}
errors = {}
def test_stream(cam_id):
    try:
        r = urllib.request.urlopen(base + "/api/stream/" + cam_id, timeout=10)
        chunk = r.read(8192)
        r.close()
        results[cam_id] = b"--frame" in chunk
    except Exception as e:
        errors[cam_id] = str(e)

threads = [threading.Thread(target=test_stream, args=("cam_0"+str(i),)) for i in range(1,7)]
for t in threads: t.start()
for t in threads: t.join()
for i in range(1,7):
    cam_id = "cam_0" + str(i)
    if cam_id in errors:
        fail("Multi-stream " + cam_id, errors[cam_id])
    elif results.get(cam_id):
        ok("Multi-stream " + cam_id + " MJPEG OK")
    else:
        fail("Multi-stream " + cam_id + " no MJPEG data")

print()
print("=== TEST 9: Invalid camera -> offline placeholder ===")
try:
    r = urllib.request.urlopen(base + "/api/stream/cam_invalid", timeout=8)
    chunk = r.read(4096)
    r.close()
    ok("Invalid cam returns MJPEG offline placeholder") if b"--frame" in chunk else fail("No MJPEG")
except Exception as e:
    fail("Invalid cam test", str(e))

print()
print("=== RESULTS: " + str(passed) + " passed, " + str(failed) + " failed ===")
sys.exit(0 if failed == 0 else 1)
