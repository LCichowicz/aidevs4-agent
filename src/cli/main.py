import sys

from src.agent.agent import Agent
from src.agent.runner import run_agent
from src.agent.state import AgentState
from src.agent.types import AgentInput, StepResult
from src.storage.runs import  save_trace

from src.tools.registry import register
from src.tools.echo import EchoTool
from src.tools.help import ToolsListTool
from src.tools.countdown import CountdownTool


def main():
    print("Wpisz 'exit' lub 'quit' by zakończyć działanie programu")
    agent = Agent()
    register(EchoTool())
    register(ToolsListTool())
    register(CountdownTool())
    while True:
        state = AgentState(steps=[])
        try:
            cli = input("Dzień dobry: ")

            if cli == "quit" or cli == "exit":
                print("Użytkownik kończy działanie programu")
                break
            
            if cli.strip() == "":
                continue

            agent_input = AgentInput(task=cli, max_steps=10)
            output = run_agent(agent, agent_input, state)
            no_of_steps = len(state.steps)
            
            save_trace(state)
            print(f"Status odpowiedzi: {output.status}; \nRezultat:\n {output.result}, \nIlość kroków: {no_of_steps}")

        except KeyboardInterrupt:
            print("Uzytkownik zakończył działanie programu")
            sys.exit(0)

if __name__ == "__main__":
    main()
