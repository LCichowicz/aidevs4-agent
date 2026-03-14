from src.llm.hub_client import HubClient



hub = HubClient()
answer = {
    "url": "https://lacteally-indignant-katheleen.ngrok-free.dev/",
    "sessionID": "proxy-test-001",
}
response = hub.submit(task="proxy", answer=answer)
print(response)