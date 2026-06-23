"""
App user performance test — 20 concurrent users across 4 pages.

All users simulate real app behaviour:
  - Cold start: full datasetSync (all data types) — worst case, no last_sync
  - Active: respond to WebSocket-triggered datasetSync pushes only
  - No direct REST calls — app reads from local SQLite, not API

User split (5 per page):
  HomeUser    (5) — DAILY_ROLLUP heartbeat every 5 min
  LiveViewUser(5) — DAILY_ROLLUP heartbeat every 5 min
  ScanLogUser (5) — SCANS sync on WebSocket push
  ManageUser  (5) — DAILY_ROLLUP heartbeat every 5 min

Scan insertion runs SEPARATELY via test_seed.py in another terminal.

Run (20 app users, 10 min):
    locust -f shared/performance/locustfile.py \
      --users 20 --spawn-rate 2 --run-time 600s --headless \
      --html reports/performance/locust_report.html

Run with live UI:
    locust -f shared/performance/locustfile.py
    open http://localhost:8089
"""

import os
import random
import sys
from datetime import datetime
from uuid import uuid4

import requests as _requests
from dotenv import load_dotenv
from locust import HttpUser, between, constant, task

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv()

from shared.api.scan_seeder import WEIGHT_RANGE_OZ, DUMMY_IMAGE_BASE64, DUMMY_DEPTH_ARRAY
from shared.data.fixtures import RESTAURANTS

API_USERNAME   = os.environ["API_USERNAME"]
API_PASSWORD   = os.environ["API_PASSWORD"]
COGNITO_CLIENT = os.environ["COGNITO_CLIENT_ID"]
BASE_URL       = os.environ.get("BASE_URL", "https://staging-mercato.skoopin.net")
RESTAURANT_ID  = os.environ.get("RESTAURANT_ID", "241")


def _build_scan() -> dict:
    r              = random.choice(list(RESTAURANTS.values()))
    station        = random.choice(list(r.stations.values()))
    venue          = random.choice(list(r.venues.values()))
    service_period = random.choice(list(r.service_periods.values()))
    menu_item      = random.choice(list(r.menu_items.values()))
    return {
        "ID":              str(uuid4()),
        "RestaurantID":    r.id,
        "StationID":       station.id,
        "VenueID":         venue.id,
        "ServicePeriodID": service_period.id,
        "MenuItemID":      menu_item.id,
        "MenuItemName":    menu_item.name,
        "Weight":          random.randint(*WEIGHT_RANGE_OZ),
        "WeightUnit":      "oz",
        "ImageBase64":     DUMMY_IMAGE_BASE64,
        "DepthArray":      DUMMY_DEPTH_ARRAY,
        "ImageType":       "jpg",
        "Type":            1,
        "WithPreSignedURL": False,
        "CapturedAt":      datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }


def _get_token() -> str:
    resp = _requests.post(
        "https://cognito-idp.us-west-2.amazonaws.com/",
        json={
            "AuthParameters": {"USERNAME": API_USERNAME, "PASSWORD": API_PASSWORD},
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": COGNITO_CLIENT,
        },
        headers={
            "x-amz-target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "content-type": "application/x-amz-json-1.1",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["AuthenticationResult"]["AccessToken"]


class _BaseAppUser(HttpUser):
    """Shared auth + cold-start datasetSync for all page users."""
    abstract = True
    host     = f"{BASE_URL}/api/v1"

    def on_start(self):
        token = _get_token()
        self.client.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "x-device-type": "ios",
        })
        self._startup_sync()

    def _startup_sync(self):
        """Cold start — full datasetSync, no last_sync timestamp (worst case)."""
        for data_type in ["SCANS", "DAILY_ROLLUP_BY_MENUS", "BEOS",
                          "MENU_ITEM_CATEGORIES", "MEAL_PERIODS", "MENU_ITEMS"]:
            self.client.get(
                "/datasetSync",
                params={
                    "data_types":           data_type,
                    "WithImagePreSignedURL": "true",
                    "RestaurantID":          RESTAURANT_ID,
                },
                name=f"GET /datasetSync [{data_type}] startup",
            )
        for data_type in ["VENUES", "RESTAURANTS"]:
            self.client.get(
                "/datasetSync",
                params={
                    "data_types":           data_type,
                    "WithImagePreSignedURL": "true",
                },
                name=f"GET /datasetSync [{data_type}] startup",
            )

    def _rollup_sync(self):
        """WebSocket push — server pushes DAILY_ROLLUP_BY_MENUS every 5 min."""
        self.client.get(
            "/datasetSync",
            params={
                "data_types":           "DAILY_ROLLUP_BY_MENUS",
                "WithImagePreSignedURL": "true",
                "RestaurantID":          RESTAURANT_ID,
            },
            name="GET /datasetSync [DAILY_ROLLUP_BY_MENUS] ws-push",
        )

    def _scans_sync(self):
        """WebSocket push — server pushes SCANS after scan insert."""
        self.client.get(
            "/datasetSync",
            params={
                "data_types":           "SCANS",
                "WithImagePreSignedURL": "true",
                "RestaurantID":          RESTAURANT_ID,
            },
            name="GET /datasetSync [SCANS] ws-push",
        )


class HomeUser(_BaseAppUser):
    """5 users on Home page. Receives DAILY_ROLLUP push every 5 min."""
    weight    = 5
    wait_time = constant(300)

    @task
    def rollup_push(self):
        self._rollup_sync()


class LiveViewUser(_BaseAppUser):
    """5 users on Live View page. Same WebSocket footprint as HomeUser."""
    weight    = 5
    wait_time = constant(300)

    @task
    def rollup_push(self):
        self._rollup_sync()


class ScanLogUser(_BaseAppUser):
    """5 users on Scan Log page. Receives SCANS push when scans are inserted."""
    weight    = 5
    wait_time = between(5, 15)

    @task
    def scans_push(self):
        self._scans_sync()


class ManageUser(_BaseAppUser):
    """5 users on Manage page. Receives DAILY_ROLLUP push every 5 min."""
    weight    = 5
    wait_time = constant(300)

    @task
    def rollup_push(self):
        self._rollup_sync()


class ScanWorker(HttpUser):
    """20 tablet workers inserting scans as fast as server responds."""
    weight    = 20
    host      = f"{BASE_URL}/api/v1"
    wait_time = constant(0)

    def on_start(self):
        token = _get_token()
        self.client.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "x-device-type": "Pad",
        })

    @task
    def post_scan(self):
        self.client.post("/scans", json=_build_scan(), name="POST /scans")
