import json
from pathlib import Path
import requests

from src.llm.hub_client import HubClient
from src.utils.artifacts import cache, save_task_artifact
from src.config import AI_DEVS_API, AI_DEVS_BASE_URL

task = 'domatowo'
CACHE_DIR = 'cache'


if __name__ == "__main__":
    hub = HubClient()

    # help =hub.submit(task=task, answer={'action': 'help'})
    # get_map = hub.submit(task=task, answer={'action': 'getMap'})

    # cache(task_name=f"{task}_help", content=help)
    # cache(task_name=f"{task}_map", content=get_map)

    # search = hub.submit(task=task, answer={'action': "searchSymbol",
    #                                        "symbol":"B3"})
    # cache(task_name=f"{task}_B3", content=search)

    # moves = ["I10", "I11", "H11", "H10"]
    # for el in moves:
    #     payload_move= {
    #         "action":"move",
    #         "object": 'bb819277fdc859c2dfe43125abb625b7',
    #         "where": el
    #     }
    #     payload_inspect =  {
    #         "action":"inspect",
    #         "object": 'bb819277fdc859c2dfe43125abb625b7',
    #     }
    #     action_move = hub.submit(task=task, answer=payload_move)
    #     action_inspect = hub.submit(task=task, answer=payload_inspect)

    #     log_payload = {"action": "getLogs"}
    #     logs = hub.submit(task=task, answer=log_payload)
    #     print(logs)

    # move_trans = {"action": "dismount",
    #               "object": 'a6f9be9d6cd65a553d3047ebee53e107',
    #               "passengers": "1"}
    
    # dismount = hub.submit(task=task, answer=move_trans)
    # print(dismount)
    answer = {'action':"callHelicopter", 'destination': "H11"}
    resque = hub.submit(task=task, answer=answer)
    save_task_artifact(task_name=task, answer=answer, response=resque )