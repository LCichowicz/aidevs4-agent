from enum import Enum
from dataclasses import is_dataclass, asdict

def to_json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value) and not isinstance(value, type):
        return to_json_safe(asdict(value))

    if (
        hasattr(value, "model_dump")
        and not isinstance(value, type)
        and callable(value.model_dump)
    ):
        return to_json_safe(value.model_dump())

    if isinstance(value, dict):
        return {
            str(k): to_json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_json_safe(v) for v in value]

    if isinstance(value, set):
        return [to_json_safe(v) for v in value]

    return repr(value)


def serialize_error(error):
    if error is None:
        return None

    if isinstance(error, Exception):
        return {
            "type": error.__class__.__name__,
            "message": str(error),
        }

    if isinstance(error, str):
        return error

    if isinstance(error, dict):
        return to_json_safe(error)

    return repr(error)

def serialize_step_result(step, step_index):
    return {
        "step_index": step_index,
        "status": step.status.value,
        "tool": step.tool,
        "tool_input": to_json_safe(step.tool_input),
        "output": to_json_safe(step.output),
        "error": serialize_error(step.error),
        "message": step.message,
    }