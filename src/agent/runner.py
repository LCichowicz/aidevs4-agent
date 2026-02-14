from .types import StepStatus, AgentOutput, AgentInput
from .agent import Agent
from .state import AgentState


def run_agent(agent: Agent, agent_input: AgentInput, state)-> AgentOutput:
    for i in range(agent_input.max_steps):
        step_result= agent.step(agent_input, state)
        state.steps.append(step_result)

        if step_result.status == StepStatus.CONTINUE:
            continue
        else:
            return AgentOutput(result=step_result.message, status = step_result.status, trace=state.steps)
    

    return AgentOutput(result="Przekroczony limit 'max_steps'", status=StepStatus.FAIL, trace=state.steps)