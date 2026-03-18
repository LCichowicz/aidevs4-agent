from pathlib import Path
from io import BytesIO
from typing import Callable


import requests
from PIL import Image

from src.llm.hub_client import HubClient
from src import config

API_KEY = config.AI_DEVS_API

CACHE_DIR = Path("cache")

RESET_URL = f"https://hub.ag3nts.org/data/{API_KEY}/electricity.png?reset=1"

CURRENT_FILE = "electricity.png"
SOLVED_FILE = "solved_electricity.png"
SOLVED_URL = "https://hub.ag3nts.org/i/solved_electricity.png"


ROTATION_PLAN={
    "1x1" : 0,
    "1x2" : 1,
    "1x3" : 1,
    "2x1" : 1,
    "2x2" : 3,
    "2x3" : 0,
    "3x1" : 1,
    "3x2" : 0,
    "3x3" : 0
}

def execute_rotation_plan(hub:HubClient):
    task = 'electricity'
    for key, value in ROTATION_PLAN.items():
        if value == 0:
            continue
        for _ in range(value):
            response = hub.submit(task=task,
                                  answer={
                                  "rotate": key},
                                  )
            print(response)



def get_cached_bytes(file_name: str, download_func: Callable[[], bytes]) -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / file_name

    if cache_file.exists():
        print(f"Loading {file_name} from cache")
        return cache_file.read_bytes()

    print(f"Downloading {file_name}")
    content = download_func()
    cache_file.write_bytes(content)
    return content


def download_current_board(hub: HubClient) -> bytes:
    return hub.download_bytes(CURRENT_FILE)


def download_solved_board() -> bytes:
    response = requests.get(SOLVED_URL, timeout=30)
    response.raise_for_status()
    return response.content


def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(image_bytes))


def main() -> None:
    requests.get(RESET_URL)

    hub = HubClient()
    hub.submit
    current_bytes = get_cached_bytes(
        file_name=CURRENT_FILE,
        download_func=lambda: download_current_board(hub),
    )

    solved_bytes = get_cached_bytes(
        file_name=SOLVED_FILE,
        download_func=download_solved_board,
    )

    execute_rotation_plan(hub)
    img = load_image_from_bytes(current_bytes)
    print(img.info)
    print(getattr(img, "text", {}))

if __name__ == "__main__":
    main()