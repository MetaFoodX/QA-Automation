"""Pytest fixtures for API tests."""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

log = logging.getLogger(__name__)

from api.auth_client import get_access_token
from config.settings import settings
from api.scan_client import ScanClient
from api.scan_seeder import ScanSeeder

USERS_FILE = Path(__file__).parent.parent / "data" / "users.yaml"
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


from data.test_constants import (
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
    from data.fixtures import RESTAURANT_A

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


@pytest.fixture(scope="session")
def seeded_basic_scans(scan_client) -> list[dict]:
    """Seed scans once per session, yield payloads, clean up at end."""
    seeder = ScanSeeder(scan_client)
    inserted = seeder.seed_concurrent()
    log.info("Seeded %d scans for test session", len(inserted))

    JSON_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = JSON_REPORT_DIR / f"seed_{timestamp}.json"
    json_path.write_text(json.dumps(inserted, indent=2))
    log.info("Seed data saved → %s", json_path)

    yield inserted
    seeder.cleanup_concurrent()