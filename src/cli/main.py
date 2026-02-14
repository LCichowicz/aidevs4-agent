import json
import sys
import time
from pathlib import Path

from src.agent.agent import Agent
from src.agent.runner import run_agent
from src.agent.state import AgentState
from src.agent.types import AgentInput, StepResult
from src.storage.runs import RUNS_DIR

def start_run()-> str:
    run_id = time.strftime("%Y%m%d_%H%M%S")
    RUNS_DIR.mkdir(exist_ok=True)

    return str(run_id)


def save_trace(run_id:str, trace: list[StepResult])->Path:

    file_path = RUNS_DIR / f"{run_id}.json"

    serialized = []
    for step in trace:
        serialized.append({
            "status": step.status.value,
            "message" : step.message
        })

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)

    return file_path


def main():
    print("Wpisz 'exit' lub 'quit' by zakończyć działanie programu")
    agent = Agent()
    state = AgentState(steps=[])
    run_id = start_run()
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

            save_trace(run_id, output.trace)
            print(f"Status odpowiedzi: {output.status}; \nRezultat:\n {output.result}, \nIlość kroków: {delta}")

        except KeyboardInterrupt:
            print("Uzytkownik zakończył działanie programu")
            sys.exit(0)

if __name__ == "__main__":
    main()
