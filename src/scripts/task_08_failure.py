from datetime import datetime
from src.llm.hub_client import HubClient
from src.llm.client import LLMClient
from src.utils.download import get_cached_or_download_text
from src.utils.artifacts import cache_text, save_task_artifact
import re

def parse_timestamp(ts_raw:str)-> tuple[str, str]:
    dt = datetime.strptime(ts_raw,"%Y-%m-%d %H:%M:%S")
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")

    return date_str, time_str

def parse_log_line(line: str)-> dict | None:
    match = re.match(r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>[A-Z]+)\]\s+(?P<message>.+)$", line)

    if not match:
        return None
    

    ts_raw = match.group("timestamp")
    level = match.group("level")
    message = match.group("message")

    date_str, time_str = parse_timestamp(ts_raw)

    content = {
        "date": date_str,
        "time": time_str,
        "level": level,
        "message": message,
    }
    return content


def msg_extract(message: str, llm: LLMClient )-> str:
    prompt = f'''You are a nuclear power plant engineer.

Rewrite the log message into a maximally concise form.

STRICT RULES:
- Keep original meaning EXACTLY (no interpretation).
- Do NOT translate.
- Do not Use UPPERCASE words.
- Do NOT create new abbreviations.
- Do NOT merge words with underscores.
- Do NOT add or invent anything.
- Keep all component names EXACTLY (e.g., ECCS8, WTANK07, FIRMWARE).
- Do NOT replace technical terms with simpler synonyms.
- Use ";" instead of multiple sentences if possible.
- Output ONLY ONE LINE.
- No quotes, no comments, no explanations.
OUTPUT EXAMPLE : ECCS8 runaway outlet temp; protection interlock initiated reactor trip
'''
 

    messages = [
    {"role": "system", "content": prompt},
    {"role": "user", "content": message},
]
    return llm.chat(messages=messages)

def merge_msg(crit_events: list, crit_msgs: dict) -> list:
    for el in crit_events:
        el['message'] = crit_msgs[el['message']]

    return crit_events

def render_log(list_of_events: list)-> str:
    unique_lines = []
    clean_log =[]
    for el in list_of_events:
        if el['message'] in unique_lines:
            continue
        unique_lines.append(el['message'])
        log_line = f"[{el['date']} {el['time']}] [{el['level']}] {el['message']}"
        clean_log.append(log_line)

    
    return "\n".join(clean_log)


if __name__ == "__main__":
    TASK = "failure"
    LOG_FILE = "failure.log"
    hub = HubClient()
    llm= LLMClient()

    crit_events = []

    logs = get_cached_or_download_text(file_name=LOG_FILE, hub_client=hub)
    logs_split = logs.split('\n')
    for line in logs_split:
        line_raw = parse_log_line(line)
        if line_raw:
            level = (line_raw.get('level') or "").strip().upper()
            if level in ['CRIT']:
                crit_events.append(line_raw)


    unique_msgs = {event['message'] for event in crit_events}
    crit_msgs ={}
    count = 1
    for element in unique_msgs:
        print(f"Msg no {count}")
        crit_msgs[element]= msg_extract(element, llm)
        count+=1
    
    cache_text("failure_crit", crit_msgs)

    formated_lines = merge_msg(crit_events, crit_msgs)

    log = render_log(formated_lines)
    print(f"Log size {len(log)}")
    cache_text("log_clean", log)

    answer = {'logs':log}

   

    response = hub.submit(
        task="failure",
        answer=answer
    )

    print(response)

    save_task_artifact(task_name="failure", answer=answer, response=response)


    