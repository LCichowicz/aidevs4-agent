from enum import Enum
from src.llm.hub_client import HubClient

if __name__ == "__main__":
    hub = HubClient()

    ACTIONS = ["start", "left", "right"]

    task = "reactor"
    action = {"command":'right'}

    response =hub.submit(task=task, answer=action)
    print(response)


