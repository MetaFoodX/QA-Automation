"""HTTP client for the Scan API."""

import allure
import requests
from requests.adapters import HTTPAdapter

from config.settings import settings

_POOL_SIZE = 55


class ScanClient:
    """Wraps POST /scans and DELETE /scans/{id} with auth."""

    def __init__(self, access_token: str):
        self.base_url = f"{settings.base_url}/api/v1"
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=_POOL_SIZE, pool_maxsize=_POOL_SIZE)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-device-type": "Pad",
        })

    def insert_scan(self, scan: dict) -> dict:
        url = f"{self.base_url}/scans"
        with allure.step(f"POST /scans [{scan.get('MenuItemName', '?')}]"):
            resp = self.session.post(url, json=scan, timeout=30)
            resp.raise_for_status()
            allure.attach(
                f"status={resp.status_code}  time={resp.elapsed.total_seconds():.3f}s",
                name="response",
                attachment_type=allure.attachment_type.TEXT,
            )
            return resp.json()

    def delete_scan(self, scan_id: str) -> None:
        with allure.step(f"DELETE /scans/{scan_id}"):
            resp = self.session.delete(f"{self.base_url}/scans/{scan_id}", timeout=30)
            resp.raise_for_status()
            allure.attach(
                f"status={resp.status_code}  time={resp.elapsed.total_seconds():.3f}s",
                name="response",
                attachment_type=allure.attachment_type.TEXT,
            )
