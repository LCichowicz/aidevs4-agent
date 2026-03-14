import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, List

from src.llm.hub_client import HubClient
from src.llm.client import LLMClient
from src.utils.artifacts import save_task_artifact


CACHE_DIR = "cache"

ALLOWED_TAGS = [
    "IT",
    "transport",
    "edukacja",
    "medycyna",
    "praca z ludźmi",
    "praca z pojazdami",
    "praca fizyczna",
]

TAGGING_SCHEMA = {
    "name": "job_tags",
    "strict": True,
    "schema": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "source_id": {"type": "integer"},
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "IT",
                            "transport",
                            "edukacja",
                            "medycyna",
                            "praca z ludźmi",
                            "praca z pojazdami",
                            "praca fizyczna",
                        ],
                    },
                },
            },
            "required": ["source_id", "tags"],
            "additionalProperties": False,
        },
    },
}


def get_cached_or_download_csv(file_name: str, hub_client: HubClient) -> str:
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


def parse_people_csv(csv_text: str) -> List[dict]:
    reader = csv.DictReader(StringIO(csv_text))

    rows = []
    for index, row in enumerate(reader, start=1):
        row["source_id"] = index
        rows.append(row)

    print(f"Długość listy: {len(rows)}")
    return rows


def extract_birth_year(row: dict) -> int:
    birth_date = row["birthDate"]
    return int(birth_date.split("-")[0])


def normalize_city(city: str) -> str:
    return city.strip().lower()


def filter_candidates(rows: List[dict]) -> List[dict]:
    candidates = []

    for row in rows:
        year = extract_birth_year(row)
        age = 2026 - year
        normalized_birth_place = normalize_city(row["birthPlace"])

        if row["gender"] != "M":
            continue

        if normalized_birth_place != "grudziądz":
            continue

        if not (20 <= age <= 40):
            continue

        row["born"] = year
        row["city"] = row["birthPlace"]
        candidates.append(row)

    print(f"Liczba kandydatów po filtrze: {len(candidates)}")
    return candidates


def build_jobs_batch(candidates: List[dict]) -> str:
    lines = []
    for row in candidates:
        source_id = row["source_id"]
        job = row["job"].strip().replace("\n", " ")
        lines.append(f"{source_id}. {job}")
    return "\n".join(lines)


def build_tagging_messages(jobs_batch: str) -> list[dict[str, str]]:
    system_prompt = """
You classify job descriptions into predefined tags.

Use only tags from the provided schema.

Base your decision only on the job description.
Do not infer unrelated information.
""".strip()

    user_prompt = f"""
Classify the following job descriptions.

Jobs:
{jobs_batch}
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_tags_map(tagged_jobs: List[dict]) -> dict[int, list[str]]:
    return {
        item["source_id"]: item["tags"]
        for item in tagged_jobs
    }


def build_answer(candidates: List[dict], tags_map: dict[int, list[str]]) -> List[dict]:
    answer = []

    for row in candidates:
        source_id = row["source_id"]
        tags = tags_map.get(source_id, [])

        if "transport" not in tags:
            continue

        answer.append({
            "name": row["name"],
            "surname": row["surname"],
            "gender": row["gender"],
            "born": row["born"],
            "city": row["city"],
            "tags": tags,
        })

    return answer


def main() -> None:
    hub = HubClient()
    llm = LLMClient()

    csv_text = get_cached_or_download_csv("people.csv", hub)
    rows = parse_people_csv(csv_text)
    candidates = filter_candidates(rows)

    jobs_batch = build_jobs_batch(candidates)
    messages = build_tagging_messages(jobs_batch)

    raw_response = llm.chat_json_schema(messages, TAGGING_SCHEMA)
    print("Raw LLM response:")
    print(raw_response)

    tags_map = {x['source_id']: x['tags'] for x in raw_response}

    answer = build_answer(candidates, tags_map)

    print(f"Liczba osób z tagiem transport: {len(answer)}")
    for item in answer[:5]:
        print(item)

    result = hub.submit("people", answer)
    print("Verify response:")
    print(result)

    save_task_artifact(
    task_name="1-people",
    answer=answer,
    response=result
)


if __name__ == "__main__":
    main()