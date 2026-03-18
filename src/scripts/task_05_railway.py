# {'ok': True, 
#  'action': 'help', 
#  'help': {'actions': [{'action': 'help', 
#                        'requires': [], 
#                        'optional': [], 
#                        'about': 'Show available actions and parameters.'}, 
#                        {'action': 'reconfigure',
#                         'requires': ['route'], 
#                         'optional': [], 
#                         'about': 'Enable reconfigure mode for the given route.'}, 
#                         {'action': 'getstatus', 'requires': ['route'], 'optional': [], 'about': 'Get current status for the given route.'}, {'action': 'setstatus', 'requires': ['route', 'value'], 'optional': [], 'about': 'Set route status while in reconfigure mode.', 'allowed_values': ['RTOPEN', 'RTCLOSE']}, {'action': 'save', 'requires': ['route'], 'optional': [], 'about': 'Exit reconfigure mode for the given route.'}], 'route_format': '[a-z]-[0-9]{1,2} (case-insensitive)', 'status_values': {'RTOPEN': 'open', 'RTCLOSE': 'close'}, 'notes': ['To change status of the road, you must first set it to "reconfigure" mode.']}}

from time import sleep
from src.llm.hub_client import HubClient

def build_railway_steps(route: str) -> list[dict]:
    return [
        {"action": "reconfigure", "route": route},
        {"action": "setstatus", "route": route, "value": "RTOPEN"},
        {"action": "save", "route": route},
    ]

def extract_retry_delay(status_code, body, headers, attempt_no: int) -> int | None:
    if isinstance(body, dict):
        retry_after = body.get("retry_after")
        if isinstance(retry_after, int | float):
            return int(retry_after) + 1

    retry_after_header = headers.get("Retry-After")
    if retry_after_header:
        try:
            return int(retry_after_header) + 1
        except ValueError:
            pass

    if status_code == 503:
        fallback = min(2 ** attempt_no, 30)
        return fallback

    return None
    
def parse_response_body(response):
    try:
        return response.json()
    except ValueError:
        return {"raw_text": response.text}

def submit_with_retry(hub, task: str, answer: dict, max_retries: int = 50) -> dict:
    attempt = 0

    while attempt < max_retries:
        attempt += 1

        response = hub.submit_raw(task, answer)
        body = parse_response_body(response)
        status = response.status_code

        print(f"[attempt={attempt}] action={answer.get('action')} status={status}")
        print(body)

        if status == 200:
            if isinstance(body, dict) and body.get("ok") is True:
                return body

            raise RuntimeError(
                f"HTTP 200, ale odpowiedź biznesowo niepoprawna: {body}"
            )

        if status in (429, 503):
            delay = extract_retry_delay(status, body, response.headers, attempt)

            if delay is None:
                raise RuntimeError(
                    f"Status {status}, ale nie udało się wyliczyć retry delay. Body: {body}"
                )

            print(f"Retry po {delay}s...")
            sleep(0.1)
            # sleep(delay)
            continue

        raise RuntimeError(
            f"Request failed. status={status}, body={body}"
        )

    raise RuntimeError(f"Max retries exceeded for action={answer.get('action')}")
  

def run_railway_flow(hub, route: str) -> dict:
    steps = build_railway_steps(route)

    for step in steps:
        response = submit_with_retry(hub, "railway", step)

        print(response)

    return response


def main():
    hub = HubClient()
    result = run_railway_flow(hub, "X-01")
    print(result)




if __name__ == "__main__":
    main()

