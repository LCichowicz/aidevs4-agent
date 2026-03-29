import requests
import json
from src.config import AI_DEVS_API
from src.llm.hub_client import HubClient


HUB_URL = "https://hub.ag3nts.org/api/"

tool_url = "books"
QUERY = "fuel efficiency"


if __name__ == "__main__":
    hub = HubClient()
    payload={
        "apikey": AI_DEVS_API,
        "query": QUERY
    }

    # response = requests.post(HUB_URL+tool_url, json=payload, timeout=15 )
    # response.raise_for_status()
    # data = response.json()
    # print(json.dumps(data, indent=2, ensure_ascii=False))    


    answer = ["rocket", "up", "up", "up","up", "up", "up","right", "right", "right", "dismount", "right",  "right",  "right"]

    
    task = "savethem"

    final_answer = hub.submit(task=task, answer=answer)
