from pathlib import Path
import json
from typing import Any

OUTPUTS_DIR = "outputs"
CACHE_DIR ="cache"


def save_task_artifact(task_name: str, answer: Any, response: Any) -> None:
    output_dir = Path(OUTPUTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"ans_{task_name}.json"

    payload = {
        "task": task_name,
        "answer": answer,
        "response": response,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved artifact: {output_file}")


def cache(task_name: str, content: Any)-> None:

    output_dir = Path(CACHE_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{task_name}.json"

    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)