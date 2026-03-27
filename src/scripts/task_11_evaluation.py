from collections import defaultdict
from pathlib import Path
from typing import Any
import json
import time

from src.llm.client import LLMClient
from src.llm.hub_client import HubClient

SENSORS_DIR = "cache/sensors"
TASK_NAME = "evaluation"
LOCAL_RESULT_PATH = "cache/evaluation_recheck.json"

SENSOR_TO_FIELD = {
    "temperature": "temperature_K",
    "pressure": "pressure_bar",
    "water": "water_level_meters",
    "voltage": "voltage_supply_v",
    "humidity": "humidity_percent",
}

VALID_RANGES = {
    "temperature_K": (553, 873),
    "pressure_bar": (60, 160),
    "water_level_meters": (5.0, 15.0),
    "voltage_supply_v": (229.0, 231.0),
    "humidity_percent": (40.0, 80.0),
}


def validate_sensor_data(data: dict) -> tuple[bool, list[dict], set[str]]:
    raw_sensor_type = data.get("sensor_type", "")
    active_sensors = {part.strip() for part in raw_sensor_type.split("/") if part.strip()}

    errors: list[dict] = []

    for sensor_name, field_name in SENSOR_TO_FIELD.items():
        value = data.get(field_name)

        if sensor_name in active_sensors:
            min_value, max_value = VALID_RANGES[field_name]

            if value is None:
                errors.append(
                    {
                        "field": field_name,
                        "type": "missing_value_for_active_sensor",
                        "value": value,
                    }
                )
                continue

            if not (min_value <= value <= max_value):
                errors.append(
                    {
                        "field": field_name,
                        "type": "out_of_range",
                        "value": value,
                        "expected_range": [min_value, max_value],
                    }
                )
        else:
            if value != 0:
                errors.append(
                    {
                        "field": field_name,
                        "type": "inactive_sensor_has_value",
                        "value": value,
                    }
                )

    data_ok = len(errors) == 0
    return data_ok, errors, active_sensors


def build_records_from_sensor_files(sensors_dir: str) -> list[dict]:
    json_files = sorted(Path(sensors_dir).glob("*.json"))
    records: list[dict] = []

    for file_path in json_files:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            data_ok, errors, active_sensors = validate_sensor_data(data)

            record = {
                "file_id": file_path.stem,
                "sensor_type": data.get("sensor_type"),
                "active_sensors": sorted(active_sensors),
                "timestamp": data.get("timestamp"),
                "operator_notes": data.get("operator_notes", ""),
                "data_ok": data_ok,
                "errors": errors,
            }
            records.append(record)

        except json.JSONDecodeError as e:
            records.append(
                {
                    "file_id": file_path.stem,
                    "sensor_type": None,
                    "active_sensors": [],
                    "timestamp": None,
                    "operator_notes": "",
                    "data_ok": False,
                    "errors": [
                        {
                            "field": None,
                            "type": "invalid_json",
                            "value": str(e),
                        }
                    ],
                }
            )
        except Exception as e:
            records.append(
                {
                    "file_id": file_path.stem,
                    "sensor_type": None,
                    "active_sensors": [],
                    "timestamp": None,
                    "operator_notes": "",
                    "data_ok": False,
                    "errors": [
                        {
                            "field": None,
                            "type": "unexpected_error",
                            "value": str(e),
                        }
                    ],
                }
            )

    return records


def normalize_note(note: str) -> str:
    if not note:
        return ""

    note = note.lower().strip()
    note = " ".join(note.split())
    note = note.rstrip(".,;:!?")
    return note


def build_notes_index(records: list[dict]) -> dict[str, dict]:
    notes_index: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "file_ids": []})

    for record in records:
        raw_note = record.get("operator_notes", "")
        normalized = normalize_note(raw_note)
        file_id = record.get("file_id")

        notes_index[normalized]["count"] += 1
        notes_index[normalized]["file_ids"].append(file_id)

    return dict(notes_index)


def chunk_list(items: list, batch_size: int) -> list[list]:
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def classify_notes_batch(llm: LLMClient, notes_batch: list[str]) -> dict[str, str]:
    """
    Zwraca:
    {
        "normalized note": "OK" | "PROBLEM" | "UNKNOWN"
    }
    """
    items = [{"id": str(i), "note": note} for i, note in enumerate(notes_batch)]

    messages = [
        {
            "role": "system",
            "content": (
                "You classify operator notes from industrial sensor logs.\n"
                "Return exactly one label for each note:\n"
                "- OK -> operator says readings are normal, acceptable, routine, approved, within limits\n"
                "- PROBLEM -> operator says readings are suspicious, wrong, anomalous, unstable, or require review\n"
                "- UNKNOWN -> the note is unclear or ambiguous\n"
                "Focus only on whether the operator claims the readings are fine or problematic."
            ),
        },
        {
            "role": "user",
            "content": (
                "Classify the notes below. Return strict JSON only.\n\n"
                f"{json.dumps(items, ensure_ascii=False)}"
            ),
        },
    ]

    schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {
                            "type": "string",
                            "enum": ["OK", "PROBLEM", "UNKNOWN"],
                        },
                    },
                    "required": ["id", "label"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }

    response = llm.chat_json_schema(messages, schema)

    id_to_note = {str(i): note for i, note in enumerate(notes_batch)}
    classified: dict[str, str] = {}

    for item in response["results"]:
        classified[id_to_note[item["id"]]] = item["label"]

    return classified


def classify_all_notes(llm: LLMClient, notes_index: dict[str, dict], batch_size: int = 100) -> dict[str, str]:
    all_notes = list(notes_index.keys())
    note_to_label: dict[str, str] = {}

    batches = chunk_list(all_notes, batch_size)
    print(f"Klasyfikuję notatki w {len(batches)} batchach...")

    for batch_no, batch in enumerate(batches, start=1):
        print(f"  batch {batch_no}/{len(batches)} | size={len(batch)}")
        batch_result = classify_notes_batch(llm, batch)
        note_to_label.update(batch_result)
        time.sleep(1.2)

    return note_to_label


def find_recheck_file_ids(records: list[dict], note_labels: dict[str, str]) -> list[str]:
    recheck_ids: list[str] = []

    for record in records:
        file_id = record["file_id"]
        data_ok = record["data_ok"]
        normalized_note = normalize_note(record.get("operator_notes", ""))
        note_label = note_labels.get(normalized_note, "UNKNOWN")

        # błędne dane zawsze są anomalią
        if not data_ok:
            recheck_ids.append(file_id)
            continue

        # dane poprawne, ale operator twierdzi, że jest problem
        if data_ok and note_label == "PROBLEM":
            recheck_ids.append(file_id)

    return sorted(set(recheck_ids))


def save_local_result(recheck_ids: list[str], path: str = LOCAL_RESULT_PATH) -> None:
    payload = {"recheck": recheck_ids}
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("Czytam pliki z danymi")
    records = build_records_from_sensor_files(SENSORS_DIR)
    print(f"Liczba rekordów: {len(records)}")

    print("Sprawdzam poprawność danych")
    invalid_records = [record for record in records if not record["data_ok"]]
    print(f"Liczba rekordów z anomaliami danych: {len(invalid_records)}")

    print("Buduję indeks notatek operatora")
    notes_index = build_notes_index(records)
    print(f"Liczba unikalnych notatek: {len(notes_index)}")

    llm = LLMClient()
    hub = HubClient()

    print("Klasyfikuję notatki przez LLM")
    note_labels = classify_all_notes(llm, notes_index, batch_size=100)

    ok_count = sum(1 for label in note_labels.values() if label == "OK")
    problem_count = sum(1 for label in note_labels.values() if label == "PROBLEM")
    unknown_count = sum(1 for label in note_labels.values() if label == "UNKNOWN")

    print("Podsumowanie klasyfikacji notatek:")
    print(f"OK: {ok_count}")
    print(f"PROBLEM: {problem_count}")
    print(f"UNKNOWN: {unknown_count}")

    print("Wyznaczam finalną listę plików do recheck")
    recheck_ids = find_recheck_file_ids(records, note_labels)
    print(f"Liczba plików do recheck: {len(recheck_ids)}")
    print("Przykładowe ID:", recheck_ids[:20])

    print("Zapisuję lokalny cache wyniku")
    save_local_result(recheck_ids)

    answer = {"recheck": recheck_ids}

    top_notes = sorted(
        notes_index.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )[:20]

    print("\nTop 20 notatek po klasyfikacji:")
    for note, meta in top_notes:
        label = note_labels.get(note, "UNKNOWN")
        print(f"[{meta['count']:>4}] {label:>8} | {note}")





    print("Wysyłam odpowiedź do centrali")
    response = hub.submit(TASK_NAME, answer)

    print("Odpowiedź centrali:")
    print(response)