from .base import Tool


_TOOLS = {}

def register(tool: Tool):
    name = tool.name.strip().lower()

    if not name:
        raise ValueError("Nazwa tool nie może być pusta")
    
    if name in _TOOLS:
        raise ValueError(f"Tool {name} już istnieje!!!")

    _TOOLS[name] = tool


def get(name: str) -> Tool | None:
    name = name.strip().lower()
    return _TOOLS.get(name)


def list_tools() -> list[Tool]:
    return list(_TOOLS.values())