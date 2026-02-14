import sys

from src.agent.agent import Agent
from src.agent.runner import run_agent
from src.agent.types import AgentInput
from src.agent.state import AgentState

def main():
    print("Wpisz 'exit' lub 'quit' by zakończyć działanie programu")
    agent = Agent()
    state = AgentState(steps=[])
    while True:
        try:
            cli = input("Dzień dobry: ")

            if cli == "quit" or cli == "exit":
                print("Użytkownik kończy działanie programu")
                break
            
            if cli.strip() == "":
                continue

            agent_input = AgentInput(task=cli, max_steps=10)
            prev = len(state.steps)
            output = run_agent(agent, agent_input, state)
            delta = len(state.steps) - prev


            print(f"Status odpowiedzi: {output.status}; \nRezultat:\n {output.result}, \nIlość kroków: {delta}")

        except KeyboardInterrupt:
            print("Uzytkownik zakończył działanie programu")
            sys.exit(0)

if __name__ == "__main__":
    main()
