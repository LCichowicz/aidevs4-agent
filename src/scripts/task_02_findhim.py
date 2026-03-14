import math
import json
from io import StringIO
from pathlib import Path
from typing import Any, List

from src.llm.hub_client import HubClient
from src.llm.client import LLMClient
from src.utils.artifacts import save_task_artifact
from src.utils.download import get_cached_or_download_text, load_person_locations_with_cache, geocode_city

ANS = "outputs"


def read_answers(file_name:str)-> dict:
    ans_dir = Path(ANS)
    ans_file = ans_dir / file_name
    
    with open(file=ans_file, encoding="utf-8") as f:
        answer_raw = json.load(f)

    return answer_raw['answer']


def collect_all_locations(hub:HubClient, suspects)-> List[dict[str,str]]:
    all_locations = []

    for suspect in suspects: 
        response_raw = load_person_locations_with_cache(hub, suspect)
        response = json.loads(response_raw)

        all_locations.append({
            "name": suspect['name'],
            "surname": suspect['surname'],
            "birthYear": suspect['born'],
            "locations": response
        })

    return all_locations

def find_best_candidate(results):

    best = None

    for r in results:
        if r["nearest"] is None:
            continue
        if best is None or r["nearest"]["distance"] < best["nearest"]["distance"]:
            best = r

    return best


def parse_power_plants(json_text: str) -> List[dict]:

    data = json.loads(json_text)
    plants = []

    for city, info in data["power_plants"].items():

        lat, lon = geocode_city(city)

        plants.append({
            "city": city,
            "code": info["code"],
            "latitude": lat,
            "longitude": lon
        })

    return plants

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Liczy odległość po powierzchni Ziemi między dwoma punktami w kilometrach."""
    earth_radius_km = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_km * c


def compute_distances(people, plants):
    results = []

    for person in people:
        best = None

        for location in person["locations"]:
            for plant in plants:

                distance = haversine_distance_km(
                    location["latitude"],
                    location["longitude"],
                    plant["latitude"],
                    plant["longitude"]
                )

                if best is None or distance < best["distance"]:
                    best = {
                        "plant_code": plant["code"],
                        "plant_city": plant["city"],
                        "distance": distance
                    }

        results.append({
            "name": person["name"],
            "surname": person["surname"],
            "birthYear": person["birthYear"],
            "nearest": best
        })

    return results

def main():

    hub = HubClient()

    ans = read_answers("ans_people.json")

    people_locations = collect_all_locations(hub, ans)

    save_task_artifact(
        task_name="locations",
        answer=people_locations,
        response=None
    )

    plants_raw = get_cached_or_download_text(
        hub_client=hub,
        file_name="findhim_locations.json"
    )

    plants = parse_power_plants(plants_raw)

    save_task_artifact(
    task_name="plants_with_coords",
    answer=plants,
    response=None
)

    distance_results = compute_distances(
        people_locations,
        plants
    )

    save_task_artifact(
        task_name="distances",
        answer=distance_results,
        response=None
    )

    best_candidate = find_best_candidate(distance_results)

    if best_candidate is None:
        raise RuntimeError("No candidate found — all distance results are empty")

    print(best_candidate)

    access_response = hub.get_access_level(
    best_candidate["name"],
    best_candidate["surname"],
    best_candidate["birthYear"],
)
    payload = {
        "name": access_response['name'],
        "surname": access_response['surname'],
        "accessLevel": access_response['accessLevel'],
        "powerPlant": best_candidate['nearest']['plant_code']
    }
    
    print(access_response)
    result = hub.submit("findhim", payload)
    print("Verify response:")
    print(result)

    save_task_artifact(
    task_name="2-findhim",
    answer=payload,
    response=result
)
 
if __name__ == "__main__":
    main()


  