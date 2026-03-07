from typing import Any
from src.tools.base import Tool
from src.agent.types import StepResult, StepStatus
from src.agent.state import AgentState

class CountdownTool(Tool):
    name = 'countdown'
    help = "odlicza malejąco do 0"

    def run(self, tool_input: dict[str, Any], state: AgentState )->StepResult:
        if "countdown" not in state.notes:
            raw_n = tool_input.get("n")
            if not raw_n:
                return StepResult(status=StepStatus.FAIL, tool=self.name, tool_input=tool_input, message="Wprowadzona wartośc musi być liczbą wiekszą od 0")
            try: 
                n = int(raw_n)
                if n <= 0:
                    return StepResult(status=StepStatus.FAIL, tool=self.name, tool_input=tool_input, message="Wartość musi być większa niż 0")
                state.notes['countdown'] = n
            except (ValueError, TypeError) as e:
                return StepResult(status=StepStatus.FAIL, tool=self.name, tool_input=tool_input, error=str(e), message=str(e))
            
            return StepResult(status=StepStatus.CONTINUE, tool=self.name, tool_input=tool_input, output={'current':n}, message=str(n))
        
        n = state.notes['countdown']
        if n > 1 :
            n -= 1
            state.notes['countdown'] = n
            return StepResult(status=StepStatus.CONTINUE, tool=self.name, tool_input=tool_input, output={'current':n}, message=str(n))
        state.notes.pop('countdown')
        return StepResult(status=StepStatus.FINAL, tool=self.name, tool_input=tool_input, message="Done!")

