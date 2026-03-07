from src.agent.state import AgentState
from src.agent.types import StepResult
from typing import Any

class Tool:
    '''
    BAse clas for all tools used by agent.
    '''
    name: str
    help: str

    def run(self, tool_input: dict[str, Any] , state: AgentState )->StepResult:
        raise NotImplementedError("Tool must implement run()")
