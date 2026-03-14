from __future__ import annotations
import requests


class PackagesClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def _post(self, payload: dict) -> dict:
        response = requests.post(
            self.base_url,
            json=payload,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()
        return data
    
    def check_package(self, package_id: str) -> dict:
        payload = {
            "apikey": self.api_key,
            "action": "check",
            "packageid": package_id,
        }

        return self._post(payload)
    

    def redirect_package(self, package_id: str, destination: str, code: str) -> dict:
        payload = {
            "apikey": self.api_key,
            "action": "redirect",
            "packageid": package_id,
            "destination": destination,
            "code": code,
        }

        return self._post(payload)