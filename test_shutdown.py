import sys, time
sys.path.insert(0, ".")

from backend.core.stream_manager import StreamManager

print("=== TEST 10: StreamManager clean shutdown ===")
mgr = StreamManager()
mgr.start_all()
time.sleep(1.5)

statuses = mgr.get_statuses()
print("  Before shutdown:")
for s in statuses:
    print("    " + s["id"] + ": " + s["status"])

print("  Stopping all streams...")
t0 = time.time()
mgr.stop_all()
elapsed = time.time() - t0
print("  stop_all() completed in " + str(round(elapsed, 2)) + "s")

if elapsed < 10.0:
    print("  PASS: All streams stopped within timeout")
else:
    print("  FAIL: Timeout exceeded")
