from typing import Any
from .types import AgentInput, StepResult, StepStatus
from .state import AgentState
from src.tools.registry import get

#TODO
#  def countdown_handler(arg:str, state: AgentState)-> StepResult:
#     if arg.strip() == "":
#         return StepResult(status=StepStatus.FAIL, message="Usage: countdown <int>")
    
#     if "countdown" not in state.notes:
#         try:
#             n = int(arg)
#         except ValueError:
#             return StepResult(status=StepStatus.FAIL, message="Countdown expects an integer")
#         state.notes['countdown'] = n
#         return StepResult(status=StepStatus.CONTINUE, message=str(n))

#     n = state.notes['countdown']
#     if n > 1:
#         n -= 1
#         state.notes['countdown'] = n
#         return StepResult(status=StepStatus.CONTINUE, message=str(n))
    
#     else:
#         state.notes.pop('countdown')
#         return StepResult(status=StepStatus.FINAL, message="Done")

def parser(task:str):

    if ":" in str(task):
        name, arg = task.split(":", maxsplit=1)
        return name.strip().lower(), arg.strip()
    elif len(task.split()) > 1:
        name, arg = task.split(" ", maxsplit=1)
        return name.strip().lower(), arg.strip()
    else:
        name = task.strip()
        arg = ""
        return name.lower(), arg

def build_tool_input(tool_name: str, arg: str)-> dict[str, Any]:
    if tool_name == "echo":
        return {'text' : arg}
    
    if tool_name == "tools":
        return {}
    
    if tool_name == "countdown":
        return {'n': arg}
    
    raise ValueError(f"unsupported tool input mapping for {tool_name}")
        
class Agent:

    def step(self, agent_input: AgentInput, state: AgentState)-> StepResult:
        task = agent_input.task.strip()

        tool_name, arg = parser(task)

        tool = get(tool_name)
        if tool is None:
            return StepResult(
                status=StepStatus.FAIL,
                tool=None,
                tool_input=None,
                output=None,
                error="Unknown command",
                message="Unknown command"
            )
        
        try:
            tool_input = build_tool_input(tool_name, arg)
        except ValueError as e:
            return StepResult(
                status=StepStatus.FAIL,
                tool=tool_name,
                error=str(e),
                message= str(e),
            )
        result = tool.run(tool_input, state)
        if result.status == StepStatus.CONTINUE and result.tool in {'echo', 'tools'}:
            return StepResult(status=StepStatus.FINAL, 
                              tool=result.tool, 
                              tool_input=result.tool_input, 
                              output=result.output,
                              error=result.error, 
                              message=result.message)
        

        return result

