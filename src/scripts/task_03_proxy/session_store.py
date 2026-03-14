from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SessionStore:
    def __init__(self, base_dir: str = "sessions") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        safe_session_id = "".join(ch for ch in session_id if ch.isalnum() or ch in ("-", "_"))
        return self.base_dir / f"{safe_session_id}.json"

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        path = self._session_path(session_id)

        if not path.exists():
            return []

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("messages", [])

    def append(self, session_id: str, role: str, content: str) -> None:
        history = self.get_history(session_id)
        history.append(
            {
                "role": role,
                "content": content,
            }
        )
        self._save(session_id, history)

    def append_tool_result(self, session_id: str, tool_name: str, result: dict[str, Any]) -> None:
        history = self.get_history(session_id)
        history.append(
            {
                "role": "tool",
                "tool_name": tool_name,
                "content": result,
            }
        )
        self._save(session_id, history)

    def _save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        path = self._session_path(session_id)

        payload = {
            "session_id": session_id,
            "messages": messages,
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)