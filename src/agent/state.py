from dataclasses import dataclass, field
from typing import Any
from .types import StepResult

@dataclass
class AgentState:
    steps: list[StepResult] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)