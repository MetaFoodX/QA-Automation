"""Scan seeder: generates N random scans across the test account and POSTs them."""
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import uuid4

from api.scan_client import ScanClient
from data.fixtures import RESTAURANTS


ALLOWED_TYPES = [1, 2, 3, 4, 7, 8, 9]
WEIGHT_RANGE_OZ = (100, 800)
DEFAULT_SCAN_COUNT = 200

DUMMY_IMAGE_BASE64 = "data:image/jpeg;base64,/9j/111"
DUMMY_DEPTH_ARRAY  = [[12, 2, 1], [2, 3, 4]]


def generate_scans(count: int) -> list[dict]:
    """Build N scan payloads with random restaurant/station/venue/menu_item/type/weight."""
    scans = []
    for _ in range(count):
        r = random.choice(list(RESTAURANTS.values()))
        station        = random.choice(list(r.stations.values()))
        venue          = random.choice(list(r.venues.values()))
        service_period = random.choice(list(r.service_periods.values()))
        menu_item      = random.choice(list(r.menu_items.values()))
        scans.append({
            "RestaurantID":     r.id,
            "StationID":        station.id,
            "VenueID":          venue.id,
            "ServicePeriodID":  service_period.id,
            "MenuItemID":       menu_item.id,
            "MenuItemName":     menu_item.name,
            "Weight":           random.randint(*WEIGHT_RANGE_OZ),
            "WeightUnit":       "oz",
            "ImageBase64":      DUMMY_IMAGE_BASE64,
            "DepthArray":       DUMMY_DEPTH_ARRAY,
            "ImageType":        "jpg",
            "Type":             random.choice(ALLOWED_TYPES),
            "WithPreSignedURL": False,
        })
    return scans


class ScanSeeder:
    def __init__(self, scan_client: ScanClient, count: int = DEFAULT_SCAN_COUNT):
        self.client = scan_client
        self.count = count
        self.inserted_payloads: list[dict] = []

    def seed(self) -> list[dict]:
        scans = generate_scans(self.count)
        base_date = datetime.now() - timedelta(days=7)

        for index, scan in enumerate(scans):
            try:
                scan["ID"] = str(uuid4())
                captured_at = base_date + timedelta(days=index % 8)
                scan["CapturedAt"] = captured_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                self.client.insert_scan(scan)
                self.inserted_payloads.append(scan)
            except Exception as e:
                print(f"Failed to insert scan {scan.get('ID')}: {e}")

        print(f"[seed] Inserted {len(self.inserted_payloads)}/{self.count} scans")
        return self.inserted_payloads

    def cleanup(self) -> None:
        failed = []
        for payload in self.inserted_payloads:
            try:
                self.client.delete_scan(payload["ID"])
            except Exception as e:
                print(f"Failed to delete scan {payload['ID']}: {e}")
                failed.append(payload)
        deleted = len(self.inserted_payloads) - len(failed)
        self.inserted_payloads = failed
        print(f"[cleanup] Deleted {deleted} scans, {len(failed)} failed")

    def seed_concurrent(self, workers: int = 20) -> list[dict]:
        scans = generate_scans(self.count)
        base_date = datetime.now() - timedelta(days=7)
        for index, scan in enumerate(scans):
            scan["ID"] = str(uuid4())
            scan["CapturedAt"] = (base_date + timedelta(days=index % 8)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        lock = threading.Lock()

        def insert(scan):
            try:
                self.client.insert_scan(scan)
                with lock:
                    self.inserted_payloads.append(scan)
            except Exception as e:
                print(f"Failed to insert scan {scan.get('ID')}: {e}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(insert, scans)

        print(f"[seed_concurrent] Inserted {len(self.inserted_payloads)}/{self.count} scans")
        return self.inserted_payloads

    def cleanup_concurrent(self, workers: int = 20) -> None:
        lock = threading.Lock()
        failed = []

        def delete(payload):
            for attempt in range(3):
                try:
                    self.client.delete_scan(payload["ID"])
                    return
                except Exception as e:
                    if attempt == 2:
                        with lock:
                            failed.append(payload)
                        print(f"Failed to delete scan {payload['ID']}: {e}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(delete, list(self.inserted_payloads))

        deleted = len(self.inserted_payloads) - len(failed)
        self.inserted_payloads = failed
        print(f"[cleanup_concurrent] Deleted {deleted} scans, {len(failed)} failed")