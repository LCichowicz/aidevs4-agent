import json
import requests
from typing import Any
from pathlib import Path
from src.llm.hub_client import HubClient


CACHE_DIR = "cache"

def get_cached_or_download_text(file_name: str, hub_client: HubClient) -> str:
    cache_dir = Path(CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / file_name

    if cache_file.exists():
        print(f"Loading {file_name} from cache")
        return cache_file.read_text(encoding="utf-8")

    print(f"Downloading {file_name} from hub")
    text = hub_client.download_text(file_name)
    cache_file.write_text(text, encoding="utf-8")
    return text

def load_person_locations_with_cache(hub: HubClient, suspect:dict)->Any :
    cache_dir = Path(CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    name = suspect['name']
    surname = suspect['surname']
    cache_file = cache_dir / f"locations_{name}_{surname}.json"

    if cache_file.exists():
        print(f"Loading {surname} locations from cache")
        return cache_file.read_text(encoding='utf-8')
    
    print(f"Downloading locations or {name} {surname}")
    response = hub.get_person_locations(name, surname)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2)
    return json.dumps(response, ensure_ascii=False)


def geocode_city(city: str) -> tuple[float, float]:

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": f"{city}, Poland",
        "format": "json",
        "limit": 1
    }

    r = requests.get(url, params=params, headers={"User-Agent": "ai-devs-script"})
    r.raise_for_status()

    data = r.json()

    if not data:
        raise RuntimeError(f"Could not geocode {city}")

    return float(data[0]["lat"]), float(data[0]["lon"])