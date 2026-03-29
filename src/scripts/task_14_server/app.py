"""
Flask server for the 'negotiations' task (task 14).

POST /find-cities
  Request:  {"params": "<natural language item query in Polish>"}
  Response: {"output": "City1,City2,..."} — comma-separated city names
  Constraints: 4 ≤ response body ≤ 500 bytes

Flow:
  1. Bielik parses the query → JSON list of item descriptions.
  2. For each item, Bielik picks the matching item code from the category list.
  3. Cities are looked up for all codes; their intersection is returned.

Run:
  python -m src.scripts.task_14_server.app
  PORT=5001 python -m src.scripts.task_14_server.app
"""

from __future__ import annotations

import logging
import os
from http import HTTPStatus

from flask import Flask, jsonify, request

from src.llm.client import LLMClient
from src.scripts.task_14_server.data_store import load_all
from src.scripts.task_14_server.matcher import resolve_items


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("task_14_server.app")


def create_app() -> Flask:
    app = Flask(__name__)

    logger.info("Loading knowledge base…")
    item_code_to_meta, city_code_to_name, item_to_cities, first_word_index = load_all()
    logger.info(
        "Loaded: %d items, %d cities, %d connections",
        len(item_code_to_meta),
        len(city_code_to_name),
        len(item_to_cities),
    )

    llm = LLMClient()

    @app.get("/health")
    def health():
        return {"status": "ok"}, HTTPStatus.OK

    @app.post("/find-cities")
    def find_cities():
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"output": "error: no JSON body"}), HTTPStatus.BAD_REQUEST

        query: str = payload.get("params", "")
        if not query or not query.strip():
            return jsonify({"output": "error: params empty"}), HTTPStatus.BAD_REQUEST

        logger.info("Query: %s", query)

        try:
            item_codes = resolve_items(
                query.strip(),
                item_code_to_meta,
                first_word_index,
                llm,
            )
        except Exception as exc:
            logger.exception("Error resolving items")
            return jsonify({"output": f"error: {exc}"}), HTTPStatus.INTERNAL_SERVER_ERROR

        logger.info("Resolved item codes: %s", item_codes)

        if not item_codes:
            return jsonify({"output": "no items matched"})

        # Build city sets for each resolved item and intersect them
        city_sets = []
        for code in item_codes:
            city_codes = item_to_cities.get(code, set())
            names = {city_code_to_name[cc] for cc in city_codes if cc in city_code_to_name}
            city_sets.append(names)

        # Intersection: cities that have ALL requested items
        result_cities = sorted(set.intersection(*city_sets)) if city_sets else []

        if not result_cities:
            output = "no cities found"
        else:
            output = ",".join(result_cities)
            # Trim to stay within the 500-byte limit
            while len(output.encode("utf-8")) > 490:
                result_cities = result_cities[:-1]
                output = ",".join(result_cities) if result_cities else "no cities found"

        logger.info("Response (%d B): %s", len(output.encode("utf-8")), output)
        return jsonify({"output": output})

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False)
