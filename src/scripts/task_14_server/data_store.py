"""
Loads and indexes CSV knowledge base for the negotiations task.
Uses parsers defined in task_14_negotiations.py.
"""

from __future__ import annotations

from pathlib import Path

from src.scripts.task_14_negotiations import (
    build_first_word_index,
    parse_cities,
    parse_connections,
    parse_items,
)
from src.utils.download import get_cached_or_download_text_no_key
from src.llm.hub_client import HubClient


def load_all() -> tuple[dict, dict, dict, dict]:
    """
    Returns:
        item_code_to_meta  – {code: {"description": str, "first_word": str}}
        city_code_to_name  – {code: name}
        item_to_cities     – {item_code: set of city_codes}
        first_word_index   – {first_word_lower: set of item_codes}
    """
    hub = HubClient()

    cities_csv = get_cached_or_download_text_no_key("s03e04_csv/cities.csv", hub)
    connections_csv = get_cached_or_download_text_no_key("s03e04_csv/connections.csv", hub)
    items_csv = get_cached_or_download_text_no_key("s03e04_csv/items.csv", hub)

    item_code_to_meta, _categories = parse_items(items_csv)
    city_code_to_name = parse_cities(cities_csv)
    item_to_cities = parse_connections(connections_csv)
    first_word_index = build_first_word_index(item_code_to_meta)

    return item_code_to_meta, city_code_to_name, item_to_cities, first_word_index
