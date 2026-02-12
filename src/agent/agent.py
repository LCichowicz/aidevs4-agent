from .types import AgentInput, StepResult, StepStatus
from .state import AgentState

class Agent:

    def step(self, agent_input: AgentInput, state: AgentState)-> StepResult:
        task = agent_input.task.strip()

        if task =="help":
            return StepResult(status=StepStatus.FINAL, message="Lista komend: \n help - zwraca listę komend\n echo: - zwraca wszystko po :")
        
        if task.startswith("echo:"):
            msg = task[len("echo:"):].strip()
            return StepResult(status=StepStatus.FINAL, message=msg)
        
        if task.startswith("countdown") and 'countdown' not in state.notes:
            msg = task[len("countdown"):].strip()
            countdown = None
            try: 
                countdown = int(msg)
            except ValueError:
                return StepResult(status=StepStatus.FAIL, message="Countdown expects an integer")
                
            state.notes["countdown"] = countdown
            return StepResult(status=StepStatus.CONTINUE, message=countdown)
        
        elif task.startswith("countdown"):
            countdown = state.notes.get("countdown")
            if not isinstance(countdown, int):
                return StepResult(status=StepStatus.FAIL, message="Internal state corrupted: countdown is not int")
            
            if countdown > 1:
                countdown -= 1
                state.notes["countdown"] = countdown
                return StepResult(status=StepStatus.CONTINUE, message=countdown)
            elif countdown == 1:
                del state.notes['countdown']
                return StepResult(status=StepStatus.FINAL, message="Done")
                 


        return StepResult(status=StepStatus.FINAL, message='Unknown Command')