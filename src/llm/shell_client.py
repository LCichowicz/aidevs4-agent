import time
import requests

from src import config

SHELL_URL = "https://hub.ag3nts.org/api/shell"
DEFAULT_BAN_WAIT = 30


class ShellClient:

    def __init__(self) -> None:
        self.api_key = config.AI_DEVS_API

    def run(self, cmd: str) -> dict:
        payload = {
            "apikey": self.api_key,
            "cmd": cmd
        }

        try:
            response = requests.post(SHELL_URL, json=payload, timeout=30)
        except requests.RequestException as e:
            return {"error": f"Request failed: {e}"}

        if response.status_code == 403:
            try:
                data = response.json()
                ban_secs = data.get("ban_duration") or data.get("wait") or DEFAULT_BAN_WAIT
                return {"error": f"Banned for {ban_secs}s — security rule violated. Wait before retrying.", "ban_seconds": ban_secs}
            except Exception:
                return {"error": f"Forbidden (403). Likely banned. Wait {DEFAULT_BAN_WAIT}s."}

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", DEFAULT_BAN_WAIT))
            return {"error": f"Rate limited. Retry after {retry_after}s.", "retry_after": retry_after}

        if response.status_code == 503:
            return {"error": "Service unavailable (503). Try again shortly."}

        if not response.ok:
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}

        try:
            return response.json()
        except ValueError:
            return {"output": response.text}

    def run_with_retry(self, cmd: str, retries: int = 3, wait: int = 30) -> dict:
        """Run a command, automatically retrying on ban/rate-limit responses."""
        for attempt in range(retries):
            result = self.run(cmd)
            if "error" not in result:
                return result
            error = result["error"]
            if "Banned" in error or "Rate limited" in error or "503" in error:
                sleep_secs = result.get("ban_seconds") or result.get("retry_after") or wait
                print(f"  [shell] Backing off {sleep_secs}s: {error}")
                time.sleep(sleep_secs)
            else:
                return result  # non-retriable error
        return result
