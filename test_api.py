import urllib.request, json, sys, time, threading

base = 'http://127.0.0.1:8000'
passed = 0
failed = 0

def ok(label):
    global passed
    passed += 1
    print(f'  PASS: {label}')

def fail(label, reason=''):
    global failed
    failed += 1
    print(f'  FAIL: {label} {reason}')

print('=== TEST 1: Application startup ===')
try:
    r = urllib.request.urlopen(base + '/', timeout=5)
    ok('GET / -> ' + str(r.status))
except Exception as e:
    fail('GET /', str(e))

print()
print('=== TEST 4: Camera status API ===')
try:
    r = urllib.request.urlopen(base + '/api/cameras', timeout=5)
    data = json.loads(r.read())
    ok('GET /api/cameras -> ' + str(r.status))
    for cam in data:
        print('    ' + cam['id'] + ': ' + cam['name'] + ' -> ' + cam['status'])
    all_online = all(c['status'] == 'ONLINE' for c in data)
    if all_online:
        ok('All 6 cameras ONLINE')
    else:
        fail('Not all cameras ONLINE')
except Exception as e:
    fail('Camera status API', str(e))

print()
print('=== TEST 5: MJPEG stream cam_01 ===')
try:
    r = urllib.request.urlopen(base + '/api/stream/cam_01', timeout=8)
    ct = r.headers.get('content-type', '')
    print('    Content-Type: ' + ct)
    chunk = r.read(8192)
    r.close()
    if b'--frame' in chunk and b'image/jpeg' in chunk:
        ok('MJPEG boundary and JPEG content-type present')
    else:
        fail('MJPEG stream headers missing')
except Exception as e:
    fail('MJPEG stream cam_01', str(e))

print()
print('=== TEST 9: Invalid camera source ===')
try:
    r = urllib.request.urlopen(base + '/api/stream/cam_invalid', timeout=8)
    chunk = r.read(4096)
    r.close()
    if b'--frame' in chunk:
        ok('Invalid camera returns offline placeholder MJPEG')
    else:
        fail('Expected MJPEG offline placeholder')
except Exception as e:
    fail('Invalid camera test', str(e))

print()
print('=== TEST 7: Multiple simultaneous streams ===')
results = {}
errors = {}

def test_stream(cam_id):
    try:
        r = urllib.request.urlopen(base + '/api/stream/' + cam_id, timeout=8)
        chunk = r.read(4096)
        r.close()
        results[cam_id] = b'--frame' in chunk
    except Exception as e:
        errors[cam_id] = str(e)

threads = [threading.Thread(target=test_stream, args=('cam_0' + str(i),)) for i in range(1, 7)]
for t in threads: t.start()
for t in threads: t.join()

for i in range(1, 7):
    cam_id = 'cam_0' + str(i)
    if cam_id in errors:
        fail('Multi-stream ' + cam_id, errors[cam_id])
    else:
        if results.get(cam_id):
            ok('Multi-stream ' + cam_id + ' MJPEG OK')
        else:
            fail('Multi-stream ' + cam_id)

print()
print('=== RESULTS: ' + str(passed) + ' passed, ' + str(failed) + ' failed ===')
sys.exit(0 if failed == 0 else 1)
