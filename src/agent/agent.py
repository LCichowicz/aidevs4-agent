from .types import AgentInput, StepResult, StepStatus
from .state import AgentState


def help_handler(arg:str, state: AgentState) -> StepResult:
    lines =[]
    for name, spec in BASIC_COMMANDS.items():
        lines.append(f"{name} - {spec['help']}")
    
    msg = "\n".join(lines)
    return StepResult(status=StepStatus.FINAL, message = msg)

def echo_handler(arg:str, state: AgentState)-> StepResult:
    msg =arg

    return StepResult(status=StepStatus.FINAL, message = msg)

def countdown_handler(arg:str, state: AgentState)-> StepResult:
    if arg.strip() == "":
        return StepResult(status=StepStatus.FAIL, message="Usage: countdown <int>")
    
    if "countdown" not in state.notes:
        try:
            n = int(arg)
        except ValueError:
            return StepResult(status=StepStatus.FAIL, message="Countdown expects an integer")
        state.notes['countdown'] = n
        return StepResult(status=StepStatus.CONTINUE, message=str(n))

    n = state.notes['countdown']
    if n > 1:
        n -= 1
        state.notes['countdown'] = n
        return StepResult(status=StepStatus.CONTINUE, message=str(n))
    
    else:
        state.notes.pop('countdown')
        return StepResult(status=StepStatus.FINAL, message="Done")


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


BASIC_COMMANDS ={
    "help": {
        "handler":help_handler,
        "help": "Pokazuje listę komend"
    },
    "echo": {
        "handler": echo_handler,
        "help": "Powtarza wpis w CLI",
    },
    "countdown": {
        "handler" :countdown_handler,
        "help": "Odlicza malejąco do 0"
    }
}
class Agent:

    def step(self, agent_input: AgentInput, state: AgentState)-> StepResult:
        task = agent_input.task.strip()

        name, arg = parser(task)

        spec = BASIC_COMMANDS.get(name)
        if spec is None:
            return StepResult(status=StepStatus.FINAL, message="Unknown command")
        
        handler = spec['handler']
        
        return handler(arg, state)

