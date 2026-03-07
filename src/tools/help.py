from typing import Any
from .base import Tool
from src.tools.registry import list_tools
from src.agent.types import StepResult, StepStatus
from src.agent.state import AgentState


class ToolsListTool(Tool):
    name = "tools"
    help = "Returns list of tools with description"
    
    def run(self, tool_input: dict[str, Any], state: AgentState)-> StepResult:
        
        tools = list_tools()

        output = []
        lines = []
        for el in tools:
            line = {"name": el.name,
                    "help": el.help}
            
            lines.append(f"{line['name']} - {line['help']}")
            output.append(line)


        msg = "\n".join(lines)

        return StepResult(status=StepStatus.CONTINUE, 
                          tool=self.name,
                          tool_input=tool_input,
                          output=output, 
                          message=msg,)