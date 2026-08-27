"""Pytest fixtures for API tests."""

import json
import logging
import os
import re
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

log = logging.getLogger(__name__)

from shared.api.auth_client import get_access_token
from shared.config.settings import settings
from shared.api.scan_client import ScanClient
from shared.api.scan_seeder import ScanSeeder
from shared.api.menu_item_client import MenuItemClient

USERS_FILE = Path(__file__).parent.parent.parent / "shared" / "data" / "users.yaml"
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
JSON_REPORT_DIR = Path(os.environ.get("JSON_REPORT_DIR", "reports/json"))


def _resolve(value: str) -> str:
    """Replace ${VAR} placeholders with env var values."""
    return ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)


def _load_user(role: str) -> dict:
    with USERS_FILE.open() as f:
        users = yaml.safe_load(f)
    return {
        "email": _resolve(users[role]["email"]),
        "password": _resolve(users[role]["password"]),
    }


@pytest.fixture(scope="session")
def access_token() -> str:
    """Session-scoped Cognito access token. Acquired once, used by all API tests."""
    user = _load_user("system")
    return get_access_token(
        username=user["email"],
        password=user["password"],
        client_id=settings.cognito_client_id,
    )

@pytest.fixture(scope="session")
def scan_client(access_token) -> ScanClient:
    """Session-scoped scan API client (auth token attached)."""
    return ScanClient(access_token=access_token)


@pytest.fixture(scope="session")
def menu_item_client(access_token) -> MenuItemClient:
    """Session-scoped menu item API client (auth token attached)."""
    return MenuItemClient(access_token=access_token)


from shared.data.test_constants import (
    CROSS_PERIOD_ITEM_ID, CROSS_PERIOD_ITEM_NAME,
    CROSS_PERIOD_REFILL_OZ, CROSS_PERIOD_LEFTOVER_OZ,
)

_DUMMY_IMAGE = "data:image/jpeg;base64,/9j/111"
_DUMMY_DEPTH = [[12, 2, 1], [2, 3, 4]]


@pytest.fixture
def seeded_cross_period_scans(scan_client) -> list[dict]:
    """Seed exactly 2 scans for cross-period meal tests, clean up after.

    Refill(Lunch, 400oz) + ServedLeftover(Dinner, 200oz) on the same day:
      All Meals consumption = max(400-200, 0) / 16 = 12.5 lb
      Lunch-only consumption = max(400-0,   0) / 16 = 25.0 lb

    Item 85537 ("Corn in a Basket") is absent from data/fixtures.py
    so the random seeder never generates scans for it.
    """
    from shared.data.fixtures import RESTAURANT_A

    captured_at = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    scans = [
        {
            "ID": str(uuid4()),
            "RestaurantID":    RESTAURANT_A.id,
            "StationID":       RESTAURANT_A.stations["s_a1"].id,
            "VenueID":         RESTAURANT_A.venues["v_a1"].id,
            "ServicePeriodID": RESTAURANT_A.service_periods["lunch"].id,
            "MenuItemID":      CROSS_PERIOD_ITEM_ID,
            "MenuItemName":    CROSS_PERIOD_ITEM_NAME,
            "Weight":          CROSS_PERIOD_REFILL_OZ,
            "WeightUnit":      "oz",
            "ImageBase64":     _DUMMY_IMAGE,
            "DepthArray":      _DUMMY_DEPTH,
            "ImageType":       "jpg",
            "Type":            1,
            "CapturedAt":      captured_at,
            "WithPreSignedURL": False,
        },
        {
            "ID": str(uuid4()),
            "RestaurantID":    RESTAURANT_A.id,
            "StationID":       RESTAURANT_A.stations["s_a1"].id,
            "VenueID":         RESTAURANT_A.venues["v_a1"].id,
            "ServicePeriodID": RESTAURANT_A.service_periods["dinner"].id,
            "MenuItemID":      CROSS_PERIOD_ITEM_ID,
            "MenuItemName":    CROSS_PERIOD_ITEM_NAME,
            "Weight":          CROSS_PERIOD_LEFTOVER_OZ,
            "WeightUnit":      "oz",
            "ImageBase64":     _DUMMY_IMAGE,
            "DepthArray":      _DUMMY_DEPTH,
            "ImageType":       "jpg",
            "Type":            2,
            "CapturedAt":      captured_at,
            "WithPreSignedURL": False,
        },
    ]

    inserted = []
    for scan in scans:
        try:
            scan_client.insert_scan(scan)
            inserted.append(scan)
        except Exception as e:
            pytest.fail(f"Failed to seed cross-period scan: {e}")

    yield inserted

    for scan in inserted:
        try:
            scan_client.delete_scan(scan["ID"])
        except Exception as e:
            log.warning("Failed to delete cross-period scan %s: %s", scan["ID"], e)


ROLLUP_SETTLE_TIMEOUT_SECONDS = 300
ROLLUP_SETTLE_POLL_INTERVAL_SECONDS = 15


def _wait_for_rollups_to_reflect_all_scans(scan_client, inserted: list[dict]) -> None:
    """Called from seeded_basic_scans right after seeding, before yield. The
    rollup that backs Consumption/Overproduction Summary is populated by the
    backend adding each scan to it one at a time, not atomically with
    insert_scan returning success -- polls GET /stats/{RestaurantID}/rollups
    per restaurant until the sum of TotalScans across every returned row
    equals how many scans we actually got a success response for (not a
    hardcoded count, so a partial seed failure is checked against correctly
    too). A plain scan count, not a value/weight match -- TotalScans is
    RefillScanCount + LeftoverScanCount, the true per-row scan count
    regardless of type. Gives up after ROLLUP_SETTLE_TIMEOUT_SECONDS.
    """
    if not inserted:
        return

    expected_by_restaurant = Counter(scan["RestaurantID"] for scan in inserted)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)  # matches ScanSeeder's own 8-day spread

    start_time = time.monotonic()
    deadline = start_time + ROLLUP_SETTLE_TIMEOUT_SECONDS
    attempt = 0
    mismatches = {}

    while time.monotonic() < deadline:
        attempt += 1
        actual_by_restaurant = {}
        for restaurant_id in expected_by_restaurant:
            url = f"{settings.base_url}/api/v1/stats/{restaurant_id}/rollups"
            params = {
                "TimeFrame": "day",
                "MenuItemCategoryID": "",
                "StartDate": start_date.isoformat(),
                "EndDate": end_date.isoformat(),
                "VenueID": "",
                "ServicePeriodID": "",
                "WithMenuItem": "true",
                "excludeWasteVenues": "true",
            }
            resp = scan_client.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            rows = resp.json().get("data", [])
            actual_by_restaurant[restaurant_id] = sum(row["RollUp"]["TotalScans"] for row in rows)

        mismatches = {
            rid: (expected, actual_by_restaurant.get(rid, 0))
            for rid, expected in expected_by_restaurant.items()
            if actual_by_restaurant.get(rid, 0) != expected
        }
        if not mismatches:
            elapsed = time.monotonic() - start_time
            log.info(
                "[seeded_basic_scans] Rollups fully settled after %d attempt(s) (~%.0fs)",
                attempt, elapsed,
            )
            return

        remaining = deadline - time.monotonic()
        summary = ", ".join(
            f"restaurant {rid}: expected {exp}, rollup shows {act}"
            for rid, (exp, act) in mismatches.items()
        )
        print(f"[seeded_basic_scans] rollup settle-check attempt {attempt}: {summary}, "
              f"~{remaining:.0f}s left — retrying in {ROLLUP_SETTLE_POLL_INTERVAL_SECONDS}s")
        time.sleep(ROLLUP_SETTLE_POLL_INTERVAL_SECONDS)

    mismatch_text = "\n".join(
        f"  restaurant {rid}: expected {exp} scan(s), rollup shows {act}"
        for rid, (exp, act) in mismatches.items()
    )
    raise TimeoutError(
        f"Rollups did not settle to reflect all {len(inserted)} seeded scan(s) within "
        f"{ROLLUP_SETTLE_TIMEOUT_SECONDS}s:\n{mismatch_text}"
    )


@pytest.fixture(scope="session")
def seeded_basic_scans(scan_client) -> list[dict]:
    """Seed scans once per session, yield payloads, clean up at end."""
    seeder = ScanSeeder(scan_client)
    inserted = seeder.seed_concurrent()
    log.info("Seeded %d scans for test session", len(inserted))

    try:
        _wait_for_rollups_to_reflect_all_scans(scan_client, inserted)
    except Exception:
        # Don't leave freshly-seeded data orphaned just because the settle-check
        # itself failed -- the code after `yield` below would otherwise never run.
        seeder.cleanup_concurrent()
        raise

    JSON_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = JSON_REPORT_DIR / f"seed_{timestamp}.json"
    json_path.write_text(json.dumps(inserted, indent=2))
    log.info("Seed data saved → %s", json_path)

    yield inserted
    seeder.cleanup_concurrent()