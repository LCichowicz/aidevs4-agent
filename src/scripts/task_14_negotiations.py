import csv
from collections import defaultdict
from typing import Tuple
from io import StringIO
from src.utils.download import get_cached_or_download_text_no_key
from src.llm.hub_client import HubClient


def parse_items(item_csv:str)-> Tuple[dict, set]:
    reader = csv.DictReader(StringIO(item_csv))
    first_words = set()
    items ={}
    for row in reader:
        description = row.get('name', "")
        tokens = description.split()
        first_word = tokens[0] if tokens else ""
        first_words.add(first_word)
        value = {
            "description" : description,
            "first_word" : first_word
        }

        items[row['code']] = value
    return items, first_words


def parse_connections(connections_csv: str)-> dict[str, set]:
    reader = csv.DictReader(StringIO(connections_csv))
    items_to_cities = {}
    for row in reader:
        item_code = row['itemCode']
        city_code = row['cityCode']

        if item_code not in items_to_cities:
            items_to_cities[item_code] = set()


        items_to_cities[item_code].add(city_code)

    # debug_print = list(items_to_cities.items())
    # print(len(debug_print))
    # print(debug_print[:5])

    return items_to_cities

def parse_cities(cities_csv: str)-> dict :
    reader = csv.DictReader(StringIO(cities_csv))
    city_code_to_name ={}
    for row in reader:
        city_code_to_name[row['code']] = row['name']
    
    return city_code_to_name

def build_first_word_index(item_code_to_meta: dict) -> dict[str, set[str]]:
    index = defaultdict(set)

    for item_code, meta in item_code_to_meta.items():
        first_word = meta.get("first_word", "").lower().strip()

        if not first_word:
            continue

        index[first_word].add(item_code)

    return dict(index)

def submit_tools(ngrok_base_url: str) -> dict:
    """Register the find-cities tool endpoint with the hub and return the response."""
    hub = HubClient()
    base = ngrok_base_url.rstrip("/")
    answer = {
        "tools": [
            {
                "URL": f"{base}/find-cities",
                "description": (
                    "Finds cities that sell items matching a natural language description. "
                    "Pass the item description (in Polish) in the 'params' field. "
                    "Returns a comma-separated list of city names. "
                    "Use this tool to discover which cities offer a specific item "
                    "needed for the wind turbine."
                ),
            }
        ]
    }
    return hub.submit(task="negotiations", answer=answer)


def check_result() -> dict:
    """Poll the hub for the async verification result."""
    hub = HubClient()
    return hub.submit(task="negotiations", answer={"action": "check"})


if __name__ == "__main__":
    import sys

    hub = HubClient()

    cities_csv = get_cached_or_download_text_no_key("s03e04_csv/cities.csv", hub)
    connections_csv = get_cached_or_download_text_no_key("s03e04_csv/connections.csv", hub)
    items_csv = get_cached_or_download_text_no_key("s03e04_csv/items.csv", hub)

    item_code_to_meta, categories = parse_items(items_csv)
    city_code_to_name = parse_cities(cities_csv)
    connections_data = parse_connections(connections_csv)
    first_word_index = build_first_word_index(item_code_to_meta)

    if len(sys.argv) == 2:
        action = sys.argv[1]
        if action == "check":
            result = check_result()
            print(result)
        else:
            # treat argument as ngrok URL — submit and then auto-poll for the flag
            import time
            print("Submitting tools…")
            submit_response = submit_tools(action)
            print("Submit response:", submit_response)

            print("\nWaiting 60 s for the agent to finish…")
            for remaining in range(60, 0, -10):
                print(f"  {remaining}s remaining…")
                time.sleep(10)

            print("\nChecking result…")
            result = check_result()
            print("Result:", result)
    else:
        print("Usage:")
        print("  python -m src.scripts.task_14_negotiations <ngrok-url>   # submit + auto-check")
        print("  python -m src.scripts.task_14_negotiations check         # manual check")
