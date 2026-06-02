"""Pytest fixtures for API tests."""

import os
import re
from pathlib import Path

import pytest
import yaml

from api.auth_client import get_access_token
from config.settings import settings
from api.scan_client import ScanClient
from api.scan_seeder import ScanSeeder

USERS_FILE = Path(__file__).parent.parent / "data" / "users.yaml"
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


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
def seeded_basic_scans(scan_client) -> list[dict]:
    """Seed scans once per session, yield payloads, clean up at end."""
    seeder = ScanSeeder(scan_client)
    inserted = seeder.seed()
    print(f"\n[seed] Inserted {len(inserted)} scans for test session")
    yield inserted
    seeder.cleanup()
    print(f"\n[cleanup] Deleted {len(inserted_ids)} scans")