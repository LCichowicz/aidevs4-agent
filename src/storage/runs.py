from pathlib import Path
import json
from src.storage.serializers import serialize_step_result

def build_trace_payload(state):
    steps = [
        serialize_step_result(step, index)
        for index, step in enumerate(state.steps)
    ]

    final_status = None
    if steps:
        final_status = steps[-1]["status"]

    return {
        "run_id": state.run_id,
        "trace_version": 1,
        "steps": steps,
        "summary": {
            "steps_count": len(steps),
            "final_status": final_status,
        },
    }

def save_trace(state):
    payload = build_trace_payload(state)
    runs_dir = Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)

    path = runs_dir / f"{state.run_id}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return path