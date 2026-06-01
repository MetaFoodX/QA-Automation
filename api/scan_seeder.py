"""Reads test scans from JSON, inserts them via API, tracks IDs for cleanup."""

import json
from pathlib import Path
from uuid import uuid4

from api.scan_client import ScanClient
from datetime import datetime, timedelta


SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "test_scenarios"


class ScanSeeder:
    def __init__(self, scan_client: ScanClient, filename: str):
        self.client = scan_client
        self.scenario_path = SCENARIOS_DIR / filename
        self.inserted_ids: list[str] = []

    def seed(self) -> list[str]:
        with self.scenario_path.open() as f:
            scans = json.load(f)

        base_date = datetime.now() - timedelta(days=7)

        for index, scan in enumerate(scans):
            try:
                scan["ID"] = str(uuid4())

                captured_at = base_date + timedelta(days=index % 8)
                scan["CapturedAt"] = captured_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

                self.client.insert_scan(scan)
                self.inserted_ids.append(scan["ID"])

            except Exception as e:
                print(f"Failed to insert scan {scan.get('ID')}: {e}")

        return self.inserted_ids

    def cleanup(self) -> None:
        for scan_id in self.inserted_ids:
            try:
                self.client.delete_scan(scan_id)
            except Exception as e:
                print(f"Failed to delete scan {scan_id}: {e}")