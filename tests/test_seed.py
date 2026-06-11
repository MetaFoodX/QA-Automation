"""Temporary benchmark: concurrent insert."""
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import uuid4

from api.scan_seeder import ScanSeeder, generate_scans, DEFAULT_SCAN_COUNT

WORKERS = 50


def test_concurrent_benchmark(scan_client):

    count = DEFAULT_SCAN_COUNT
    print(f"\n--- CONCURRENT {WORKERS} workers ({count} scans) ---")

    scans = generate_scans(count)
    base_date = datetime.now() - timedelta(days=7)
    for i, scan in enumerate(scans):
        scan["ID"] = str(uuid4())
        scan["CapturedAt"] = (base_date + timedelta(days=i % 8)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    lock          = threading.Lock()
    inserted      = []
    request_times = []
    session_start = time.perf_counter()

    def insert_timed(scan):
        thread_name = threading.current_thread().name
        sent_at     = time.perf_counter() - session_start
        t           = time.perf_counter()
        scan_client.insert_scan(scan)
        duration    = time.perf_counter() - t
        done_at     = time.perf_counter() - session_start
        with lock:
            inserted.append(scan)
            request_times.append({
                "thread":   thread_name,
                "sent_at":  sent_at,
                "done_at":  done_at,
                "duration": duration,
            })

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        executor.map(insert_timed, scans)
    con_elapsed = time.perf_counter() - t0

    durations = [r["duration"] for r in request_times]
    avg_ms    = (sum(durations) / len(durations)) * 1000
    min_ms    = min(durations) * 1000
    max_ms    = max(durations) * 1000

    max_overlap = 0
    for r in request_times:
        overlap = sum(
            1 for other in request_times
            if other["sent_at"] < r["done_at"] and other["done_at"] > r["sent_at"]
        )
        max_overlap = max(max_overlap, overlap)

    theoretical_min = (avg_ms / 1000) * (count / WORKERS)

    print(f"Total wall time  : {con_elapsed:.2f}s")
    print(f"Per request avg  : {avg_ms:.0f}ms  (min={min_ms:.0f}ms  max={max_ms:.0f}ms)")
    print(f"Max in-flight    : {max_overlap} requests overlapping at once")
    print(f"Theoretical min  : {theoretical_min:.2f}s  (if server handled {WORKERS} truly in parallel)")
    print(f"Actual vs theory : {con_elapsed / theoretical_min:.1f}x slower than ideal")
    print(f"→ Server is queuing ~{int(con_elapsed / (avg_ms / 1000))}/{count} requests serially")

    # Per-thread breakdown
    thread_stats = defaultdict(list)
    for r in request_times:
        thread_stats[r["thread"]].append(r["duration"])

    print(f"\n{'Thread':<20} {'Requests':>9} {'Avg wait':>10} {'Max wait':>10} {'Total wait':>12}")
    print("-" * 65)
    for thread, times in sorted(thread_stats.items()):
        avg = sum(times) / len(times) * 1000
        mx  = max(times) * 1000
        tot = sum(times) * 1000
        print(f"{thread:<20} {len(times):>9} {avg:>9.0f}ms {mx:>9.0f}ms {tot:>11.0f}ms")

    # Cleanup
    seeder_con = ScanSeeder(scan_client)
    seeder_con.inserted_payloads = inserted
    t0 = time.perf_counter()
    seeder_con.cleanup_concurrent(workers=WORKERS)
    print(f"Cleanup          : {time.perf_counter() - t0:.2f}s")
