"""
App user performance test — reactive scan-driven load simulation.

Real app flow (simulated here):
  1. Tablet worker inserts a scan   → POST /scans
  2. Server fires WebSocket push    → all 20 connected app users receive dataset-sync-changed
  3. Each app user calls both:
       GET /datasetSync [DAILY_ROLLUP_BY_MENUS]
       GET /datasetSync [SCANS]

Per scan insert: 20 rollup calls + 20 scans calls hit the server simultaneously.
With 20 workers × 1 scan/40s = 0.5 scans/s → 10 rollup calls/s + 10 scans calls/s.

User split:
  HomeUser    (5) — Home page
  LiveViewUser(5) — Live View page
  ManageUser  (5) — Manage page
  ScanLogUser (5) — Scan Log page
  ScanWorker (20) — tablet, inserts 1 scan every 40s

Run (20 app users + 20 scan workers, 10 min):
    mkdir -p reports/performance && \
    locust -f shared/performance/locustfile.py \
      --users 40 --spawn-rate 4 --run-time 600s --headless \
      --html reports/performance/locust_report.html && \
    python shared/performance/inject_summary.py \
      --html reports/performance/locust_report.html
"""

import logging
import os
import random
import sys
from datetime import datetime
from uuid import uuid4

import gevent
import gevent.queue
import requests as _requests
from dotenv import load_dotenv
from locust import HttpUser, constant, task

log = logging.getLogger("perf")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv()

from shared.api.scan_seeder import WEIGHT_RANGE_OZ, DUMMY_IMAGE_BASE64, DUMMY_DEPTH_ARRAY, CATEGORY_TYPES, ALLOWED_TYPES_ALL
from shared.data.fixtures import RESTAURANTS

API_USERNAME   = os.environ.get("PERF_USERNAME", os.environ["API_USERNAME"])
API_PASSWORD   = os.environ.get("PERF_PASSWORD", os.environ["API_PASSWORD"])
COGNITO_CLIENT = os.environ["COGNITO_CLIENT_ID"]
BASE_URL       = os.environ.get("BASE_URL", "https://staging-mercato.skoopin.net")
RESTAURANT_ID  = os.environ.get("RESTAURANT_ID", "241")

# All app user queues. ScanWorker puts a signal here after every successful scan.
_app_queues: list[gevent.queue.Queue] = []


def _broadcast_scan_event():
    for q in _app_queues:
        q.put_nowait(1)


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
        "Type":            random.choice(CATEGORY_TYPES.get(menu_item.category, ALLOWED_TYPES_ALL)),
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


def _curl(r) -> str:
    req = r.request
    headers = " ".join(f'-H "{k}: {v}"' for k, v in req.headers.items())
    body = f"-d '{req.body}'" if req.body else ""
    return f"curl -X {req.method} '{req.url}' {headers} {body}".strip()


def _log_response(name: str, r) -> dict:
    try:
        body  = r.json()
        count = len(body.get("data", [])) if isinstance(body, dict) else "?"
        log.info("[%d] %s — %dms — rows=%s", r.status_code, name, r.elapsed.total_seconds() * 1000, count)
        return body
    except Exception:
        log.info("[%d] %s — %dms", r.status_code, name, r.elapsed.total_seconds() * 1000)
        return {}


class _BaseAppUser(HttpUser):
    abstract  = True
    host      = f"{BASE_URL}/api/v1"
    wait_time = constant(0)  # no fixed timer — driven by scan events

    def on_start(self):
        token = _get_token()
        self.client.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "x-device-type": "ios",
        })
        self._startup_sync()
        self._queue = gevent.queue.Queue()
        _app_queues.append(self._queue)

    def on_stop(self):
        if self._queue in _app_queues:
            _app_queues.remove(self._queue)

    def _startup_sync(self):
        """Cold start — full datasetSync for all types (no last_sync timestamp)."""
        for data_type in ["SCANS", "DAILY_ROLLUP_BY_MENUS", "BEOS",
                          "MENU_ITEM_CATEGORIES", "MEAL_PERIODS", "MENU_ITEMS"]:
            with self.client.get(
                "/datasetSync",
                params={
                    "data_types":           data_type,
                    "WithImagePreSignedURL": "true",
                    "RestaurantID":          RESTAURANT_ID,
                },
                name=f"GET /datasetSync [{data_type}] startup",
                catch_response=True,
            ) as r:
                _log_response(f"GET /datasetSync [{data_type}] startup", r)
        for data_type in ["VENUES", "RESTAURANTS"]:
            with self.client.get(
                "/datasetSync",
                params={
                    "data_types":           data_type,
                    "WithImagePreSignedURL": "true",
                },
                name=f"GET /datasetSync [{data_type}] startup",
                catch_response=True,
            ) as r:
                _log_response(f"GET /datasetSync [{data_type}] startup", r)

    def _rollup_sync(self):
        with self.client.get(
            "/datasetSync",
            params={
                "data_types":           "DAILY_ROLLUP_BY_MENUS",
                "WithImagePreSignedURL": "true",
                "RestaurantID":          RESTAURANT_ID,
            },
            name="GET /datasetSync [DAILY_ROLLUP_BY_MENUS] ws-push",
            catch_response=True,
        ) as r:
            import json as _json
            body = _log_response("GET /datasetSync [DAILY_ROLLUP_BY_MENUS] ws-push", r)
            log.info("ROLLUP CURL:\n%s", _curl(r))
            log.info("ROLLUP RESPONSE:\n%s", _json.dumps(body, indent=2))
            if not body or not body.get("success"):
                r.failure(f"success!=true: {body}")
            elif not body.get("data", {}).get("DAILY_ROLLUP_BY_MENUS"):
                r.failure("DAILY_ROLLUP_BY_MENUS returned empty")

    def _scans_sync(self):
        with self.client.get(
            "/datasetSync",
            params={
                "data_types":           "SCANS",
                "WithImagePreSignedURL": "true",
                "RestaurantID":          RESTAURANT_ID,
            },
            name="GET /datasetSync [SCANS] ws-push",
            catch_response=True,
        ) as r:
            import json as _json
            body = _log_response("GET /datasetSync [SCANS] ws-push", r)
            log.info("SCANS CURL:\n%s", _curl(r))
            log.info("SCANS RESPONSE:\n%s", _json.dumps(body, indent=2))
            if not body or not body.get("success"):
                r.failure(f"success!=true: {body}")
            elif not body.get("data", {}).get("SCANS"):
                r.failure("SCANS returned empty")

    @task
    def on_scan_event(self):
        """Wait for a scan insert, then immediately fire rollup + scans without blocking."""
        self._queue.get()
        gevent.spawn(self._rollup_sync)
        gevent.spawn(self._scans_sync)


class HomeUser(_BaseAppUser):
    """5 users on Home page."""
    weight = 5


class LiveViewUser(_BaseAppUser):
    """5 users on Live View page."""
    weight = 5


class ManageUser(_BaseAppUser):
    """5 users on Manage page."""
    weight = 5


class ScanLogUser(_BaseAppUser):
    """5 users on Scan Log page."""
    weight = 5


class ScanWorker(HttpUser):
    """20 tablet workers — 1 scan every 40s. Broadcasts to all app users on success."""
    weight    = 20
    host      = f"{BASE_URL}/api/v1"
    wait_time = constant(40)

    def on_start(self):
        token = _get_token()
        self.client.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "x-device-type": "Pad",
        })
        gevent.sleep(20)  # wait for all app users to finish startup and register queues

    @task
    def post_scan(self):
        with self.client.post("/scans", json=_build_scan(), name="POST /scans", catch_response=True) as r:
            _log_response("POST /scans", r)
            if r.status_code in (200, 201):
                _broadcast_scan_event()
