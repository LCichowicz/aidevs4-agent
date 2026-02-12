import sys

from src.agent.agent import Agent
from src.agent.runner import run_agent
from src.agent.types import AgentInput

def main():
    print("Wpisz 'exit' lub 'quit' by zakończyć działanie programu")
    while True:
        try:
            cli = input("Dzień dobry: ")

            if cli == "quit" or cli == "exit":
                print("Użytkownik kończy działanie programu")
                break
            
            if cli.strip() == "":
                continue

            agent_input = AgentInput(task=cli, max_steps=10)
            agent = Agent()
            output = run_agent(agent, agent_input)



            print(f"Status odpowiedzi: {output.status}; Rezultat: {output.result}, Ilość kroków: {len(output.trace)}")

        except KeyboardInterrupt:
            print("Uzytkownik zakończył działanie programu")
            sys.exit(0)

if __name__ == "__main__":
    main()
