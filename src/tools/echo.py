from typing import Any
from .base import Tool
from src.agent.types import StepResult, StepStatus
from src.agent.state import AgentState

class EchoTool(Tool):
    name = "echo"
    help = "Powtarza wpis w CLI"

    def run(self, tool_input: dict[str, Any], state:AgentState) -> StepResult:
        raw = tool_input.get('text')
        if not isinstance(raw, str):
            return StepResult(status=StepStatus.FAIL, 
                              tool=self.name, 
                              tool_input=tool_input, 
                              error="Echo expects text",
                              output=None, 
                              message='Wrong input type',
                              )
        
        if not raw.strip():
            return StepResult(status=StepStatus.FAIL, 
                              tool=self.name, 
                              tool_input=tool_input, 
                              error="Echo expects non empty text",
                              output=None, 
                              message='Usage: echo <text>',
                              )

        text = raw.strip()
        return StepResult(status=StepStatus.CONTINUE, 
                              tool=self.name, 
                              tool_input=tool_input, 
                              output={"text": text}, 
                              message=text,
                              )