from dataclasses import dataclass
from typing import Any, Optional, List
from enum import Enum

class StepStatus(Enum):
    CONTINUE = "CONTINUE"
    FINAL = "FINAL"
    FAIL = "FAIL"
    NEED_INPUT = "NEED_INPUT"


@dataclass(frozen=True)
class AgentInput:
    task:str
    context:Optional[Any] = None
    max_steps: int = 10

@dataclass(frozen=True)
class StepResult:
    status : StepStatus
    message: Optional[Any] = None

@dataclass
class AgentOutput:
    result: Optional[str]
    status: StepStatus
    trace: List[StepResult]
