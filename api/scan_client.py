"""HTTP client for the Scan API."""

import requests

from config.settings import settings


class ScanClient:
    """Wraps POST /scans and DELETE /scans/{id} with auth."""

    def __init__(self, access_token: str):
        self.base_url = f"{settings.base_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-device-type": "Pad",
        })

    def insert_scan(self, scan: dict) -> dict:
        url = f"{self.base_url}/scans"

        print(f"\n[scan_client] POST {url}")
        print(f"[scan_client] Scan ID: {scan.get('ID')}")

        resp = self.session.post(url, json=scan, timeout=30)

        print(f"[scan_client] Status Code: {resp.status_code}")
        print(f"[scan_client] Response: {resp.text}")

        resp.raise_for_status()
        return resp.json()

    def delete_scan(self, scan_id: str) -> None:
        """DELETE a scan by ID."""
        resp = self.session.delete(f"{self.base_url}/scans/{scan_id}", timeout=30)
        resp.raise_for_status()