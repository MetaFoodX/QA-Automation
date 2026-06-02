"""Temporary smoke test: verify seed creates scans and cleanup deletes them."""
from api.scan_seeder import ScanSeeder


def test_seed_and_cleanup(scan_client):
    seeder = ScanSeeder(scan_client, count=50)

    print("\n--- SEEDING 10 SCANS ---")
    payloads = seeder.seed()
    print(f"Inserted: {len(payloads)} scans\n")

    for i, p in enumerate(payloads, 1):
        print(f"\n[{i}] {p}")

    print("\n--- CLEANING UP ---")
    seeder.cleanup()
    print("Done.")