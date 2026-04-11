# import json
# from time import sleep
# from src.config import AI_DEVS_API
# from src.llm.hub_client import HubClient
# from src.utils.artifacts import cache


# HUB_URL = "https://hub.ag3nts.org/api/"

# task = 'windpower'

# from typing import Any




    
# if __name__ == "__main__":
#     hub = HubClient()



#     hub.submit(task=task, answer={"action": "start"})

#     for el in params:
#         answer={
#             "action": "get",
#             "param": el
#         }



#         task_answer = hub.submit(task=task, answer=answer)

#     collected = {}
#     expected ={"weather", "turbinecheck", "powerplantcheck"}
#     max_attempt = 20
#     while set(collected.keys()) != expected and max_attempt > 0:
#         response = hub.submit(task=task, answer={"action":"getResult"})



#         source = response.get("sourceFunction")

#         if not source:
#             print("Notting yet...")
#             sleep(0.3)
#             continue
#         else:
#             collected[source] = response
#             cache(task_name=f"{task}_{source}", content=response)
#             print(json.dumps(response, indent=2))

#         max_attempt-= 1

#     required_kw = 4.0
#     storms, production = find_storms_and_first_valid_production_slot(
#         weather_report=collected['weather'],
#         required_kw=required_kw,
#     )

#     print("STORMS:")
#     print(json.dumps(storms, indent=2))

#     print("PRODUCTION:")
#     print(json.dumps(production, indent=2))

import json
import re
from time import sleep, monotonic
from typing import Any

from src.llm.hub_client import HubClient
from src.utils.artifacts import cache


TASK = "windpower"

INITIAL_REPORTS = ["weather", "powerplantcheck"]

CUT_OFF_WIND_MS = 14.0
MIN_OPERATIONAL_WIND_MS = 4.0
RATED_POWER_KW = 14.0

GET_RESULT_SLEEP_S = 0.08
MAX_GET_RESULT_ATTEMPTS = 500

DEFAULT_MARGIN_S = 1.2
FINAL_CHECK_MARGIN_S = 0.35
DONE_MARGIN_S = 0.05


def split_timestamp(timestamp: str) -> tuple[str, str]:
    date_part, hour_part = timestamp.split(" ")
    return date_part, hour_part


def parse_required_power_kw(powerplant_report: dict[str, Any]) -> float:
    raw = powerplant_report.get("powerDeficitKw")
    if raw is None:
        raise ValueError("Missing powerDeficitKw in powerplantcheck response")

    if isinstance(raw, (int, float)):
        return float(raw)

    if not isinstance(raw, str):
        raise ValueError(f"Unsupported powerDeficitKw type: {type(raw)}")

    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    if not numbers:
        raise ValueError(f"Could not parse powerDeficitKw from value: {raw}")

    return max(float(x) for x in numbers)


def interpolate(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    if x2 == x1:
        return y1
    ratio = (x - x1) / (x2 - x1)
    return y1 + ratio * (y2 - y1)


def estimate_wind_yield(wind_ms: float) -> float:
    """
    Interpolacja między punktami z dokumentacji.
    Punkty oparte o środki zakresów:
      4  -> 12.5%
      6  -> 35%
      8  -> 65%
      10 -> 95%
      12 -> 100%
      14 -> 100%
    """
    if wind_ms < 4:
        return 0.0
    if wind_ms > 14:
        return 0.0

    anchors = [
        (4.0, 0.125),
        (6.0, 0.35),
        (8.0, 0.65),
        (10.0, 0.95),
        (12.0, 1.00),
        (14.0, 1.00),
    ]

    if wind_ms <= anchors[0][0]:
        return anchors[0][1]

    for idx in range(len(anchors) - 1):
        x1, y1 = anchors[idx]
        x2, y2 = anchors[idx + 1]
        if x1 <= wind_ms <= x2:
            return interpolate(wind_ms, x1, y1, x2, y2)

    return 1.0


def estimate_power_kw(
    wind_ms: float,
    pitch_angle: int,
    rated_power_kw: float = RATED_POWER_KW,
) -> float:
    if pitch_angle not in (0, 45, 90):
        raise ValueError(f"Unsupported pitch angle: {pitch_angle}")

    pitch_multiplier = {
        0: 1.0,
        45: 0.65,
        90: 0.0,
    }[pitch_angle]

    wind_yield = estimate_wind_yield(wind_ms)
    return rated_power_kw * wind_yield * pitch_multiplier


def find_storms_and_best_production_slot(
    weather_report: dict[str, Any],
    required_kw: float,
    cutoff_wind_ms: float = CUT_OFF_WIND_MS,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    forecast = weather_report.get("forecast")
    if not isinstance(forecast, list):
        raise ValueError("weather_report does not contain valid 'forecast' list")

    storm_configs: list[dict[str, Any]] = []
    first_valid_slot: dict[str, Any] | None = None
    best_slot: dict[str, Any] | None = None

    for point in forecast:
        timestamp = point.get("timestamp")
        wind_ms = point.get("windMs")

        if timestamp is None or wind_ms is None:
            continue

        start_date, start_hour = split_timestamp(timestamp)

        if wind_ms > cutoff_wind_ms:
            storm_configs.append(
                {
                    "startDate": start_date,
                    "startHour": start_hour,
                    "windMs": wind_ms,
                    "pitchAngle": 90,
                    "turbineMode": "idle",
                }
            )
            continue

        if MIN_OPERATIONAL_WIND_MS <= wind_ms <= cutoff_wind_ms:
            estimated_power = estimate_power_kw(wind_ms=wind_ms, pitch_angle=0)

            candidate = {
                "startDate": start_date,
                "startHour": start_hour,
                "windMs": wind_ms,
                "pitchAngle": 0,
                "turbineMode": "production",
                "estimatedPowerKw": round(estimated_power, 2),
            }

            if best_slot is None or candidate["estimatedPowerKw"] > best_slot["estimatedPowerKw"]:
                best_slot = candidate

            if first_valid_slot is None and estimated_power >= required_kw:
                first_valid_slot = candidate

    return storm_configs, (first_valid_slot or best_slot)


def submit_action(hub: HubClient, answer: dict[str, Any]) -> dict[str, Any]:
    return hub.submit(task=TASK, answer=answer)


def ensure_time_left(start_ts: float, session_timeout_s: float, extra_margin_s: float = DEFAULT_MARGIN_S) -> None:
    elapsed = monotonic() - start_ts
    remaining = session_timeout_s - elapsed
    if remaining <= extra_margin_s:
        raise RuntimeError(f"Too little time left: {remaining:.2f}s")


def enqueue_initial_reports(hub: HubClient) -> None:
    for param in INITIAL_REPORTS:
        response = submit_action(
            hub,
            {
                "action": "get",
                "param": param,
            },
        )
        print(f"[QUEUE] {param}: {json.dumps(response, ensure_ascii=False)}")


def collect_expected_reports(
    hub: HubClient,
    expected: set[str],
    start_ts: float,
    session_timeout_s: float,
    max_attempts: int = MAX_GET_RESULT_ATTEMPTS,
    sleep_s: float = GET_RESULT_SLEEP_S,
) -> dict[str, Any]:
    collected: dict[str, Any] = {}
    attempts = 0

    while set(collected.keys()) != expected and attempts < max_attempts:
        ensure_time_left(start_ts, session_timeout_s)
        attempts += 1

        response = submit_action(hub, {"action": "getResult"})
        source = response.get("sourceFunction")

        if not source:
            sleep(sleep_s)
            continue

        if source in expected and source not in collected:
            collected[source] = response
            cache(task_name=f"{TASK}_{source}", content=response)
            print(f"[OK] got {source} ({len(collected)}/{len(expected)})")
            print(json.dumps(response, indent=2, ensure_ascii=False))

    missing = expected - set(collected.keys())
    if missing:
        raise RuntimeError(f"Did not collect all expected reports. Missing: {missing}")

    return collected


def build_unlock_request_key(config: dict[str, Any]) -> str:
    return f"{config['startDate']} {config['startHour']}|{config['windMs']}|{config['pitchAngle']}"


def extract_unlock_code(unlock_response: dict[str, Any]) -> str:
    candidates = ["unlockCode", "code", "signature", "result", "value"]

    for key in candidates:
        value = unlock_response.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for value in unlock_response.values():
        if isinstance(value, str) and value.strip() and len(value.strip()) >= 8:
            return value.strip()

    raise ValueError(
        f"Could not extract unlock code from response: {json.dumps(unlock_response, ensure_ascii=False)}"
    )


def enqueue_unlock_code_requests(hub: HubClient, configs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    keyed_configs: dict[str, dict[str, Any]] = {}

    for config in configs:
        key = build_unlock_request_key(config)
        keyed_configs[key] = config

        response = submit_action(
            hub,
            {
                "action": "unlockCodeGenerator",
                "startDate": config["startDate"],
                "startHour": config["startHour"],
                "windMs": config["windMs"],
                "pitchAngle": config["pitchAngle"],
            },
        )
        print(f"[QUEUE] unlockCodeGenerator for {key}: {json.dumps(response, ensure_ascii=False)}")

    return keyed_configs


def collect_unlock_codes_parallel(
    hub: HubClient,
    keyed_configs: dict[str, dict[str, Any]],
    start_ts: float,
    session_timeout_s: float,
) -> list[dict[str, Any]]:
    """
    Zakładamy, że odpowiedzi unlockCodeGenerator wracają w tej samej liczbie,
    ale niekoniecznie w tej samej kolejności.

    Ponieważ API nie daje jawnego correlation id, mapujemy je FIFO
    po kolejności wysłanych requestów. To nie jest piękne, ale przy tym API
    jest najbardziej praktyczne.
    """
    pending_keys = list(keyed_configs.keys())
    final_configs: list[dict[str, Any]] = []

    attempts = 0
    while pending_keys and attempts < MAX_GET_RESULT_ATTEMPTS:
        ensure_time_left(start_ts, session_timeout_s)
        attempts += 1

        response = submit_action(hub, {"action": "getResult"})
        source = response.get("sourceFunction")

        if not source:
            sleep(GET_RESULT_SLEEP_S)
            continue

        if source != "unlockCodeGenerator":
            print(f"[SKIP] unlock collector got unrelated response: {source}")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            continue

        unlock_code = extract_unlock_code(response)
        current_key = pending_keys.pop(0)
        config = keyed_configs[current_key]

        final_configs.append(
            {
                **config,
                "unlockCode": unlock_code,
            }
        )

        print(f"[OK] unlock received for {current_key}")
        print(json.dumps(response, indent=2, ensure_ascii=False))

    if pending_keys:
        raise RuntimeError(f"Did not receive all unlock codes. Missing for keys: {pending_keys}")

    return final_configs


def build_config_payload(configs: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for config in configs:
        timestamp_key = f"{config['startDate']} {config['startHour']}"
        payload[timestamp_key] = {
            "pitchAngle": config["pitchAngle"],
            "turbineMode": config["turbineMode"],
            "unlockCode": config["unlockCode"],
        }

    return payload


def run_final_turbinecheck(
    hub: HubClient,
    start_ts: float,
    session_timeout_s: float,
) -> dict[str, Any]:
    ensure_time_left(start_ts, session_timeout_s, extra_margin_s=FINAL_CHECK_MARGIN_S)

    queue_response = submit_action(
        hub,
        {
            "action": "get",
            "param": "turbinecheck",
        },
    )
    print(f"[QUEUE] final turbinecheck: {json.dumps(queue_response, ensure_ascii=False)}")

    attempts = 0
    while attempts < MAX_GET_RESULT_ATTEMPTS:
        attempts += 1

        # tu świadomie dużo luźniejszy guard
        ensure_time_left(start_ts, session_timeout_s, extra_margin_s=0.05)

        response = submit_action(hub, {"action": "getResult"})
        source = response.get("sourceFunction")

        if not source:
            sleep(GET_RESULT_SLEEP_S)
            continue

        if source != "turbinecheck":
            print(f"[SKIP] final turbinecheck wait got unrelated response: {source}")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            continue

        cache(task_name=f"{TASK}_final_turbinecheck", content=response)
        print("[OK] final turbinecheck received")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return response

    raise RuntimeError("Final turbinecheck was not returned")


def main() -> None:
    hub = HubClient()

    start_response = submit_action(hub, {"action": "start"})
    print("[START]")
    print(json.dumps(start_response, indent=2, ensure_ascii=False))

    session_timeout_s = float(start_response.get("sessionTimeout", 40))
    run_start_ts = monotonic()

    enqueue_initial_reports(hub)

    collected = collect_expected_reports(
        hub=hub,
        expected={"weather", "powerplantcheck"},
        start_ts=run_start_ts,
        session_timeout_s=session_timeout_s,
    )

    weather_report = collected["weather"]
    powerplant_report = collected["powerplantcheck"]

    required_kw = parse_required_power_kw(powerplant_report)
    print(f"[INFO] required power: {required_kw} kW")

    storms, production = find_storms_and_best_production_slot(
        weather_report=weather_report,
        required_kw=required_kw,
    )

    print("[INFO] storm configs:")
    print(json.dumps(storms, indent=2, ensure_ascii=False))

    print("[INFO] chosen production slot:")
    print(json.dumps(production, indent=2, ensure_ascii=False))

    if production is None:
        raise RuntimeError("No production candidate found at all")

    configs_without_unlock = storms + [production]

    sanitized_configs: list[dict[str, Any]] = []
    for config in configs_without_unlock:
        sanitized_configs.append(
            {
                "startDate": config["startDate"],
                "startHour": config["startHour"],
                "windMs": config["windMs"],
                "pitchAngle": config["pitchAngle"],
                "turbineMode": config["turbineMode"],
            }
        )

    print("[INFO] configs before unlockCode:")
    print(json.dumps(sanitized_configs, indent=2, ensure_ascii=False))

    ensure_time_left(run_start_ts, session_timeout_s)

    keyed_configs = enqueue_unlock_code_requests(hub, sanitized_configs)
    final_configs = collect_unlock_codes_parallel(
        hub=hub,
        keyed_configs=keyed_configs,
        start_ts=run_start_ts,
        session_timeout_s=session_timeout_s,
    )

    print("[INFO] configs with unlockCode:")
    print(json.dumps(final_configs, indent=2, ensure_ascii=False))
    cache(task_name=f"{TASK}_configs_with_unlock", content=final_configs)

    config_payload = build_config_payload(final_configs)

    ensure_time_left(run_start_ts, session_timeout_s, extra_margin_s=0.4)
    config_response = submit_action(
        hub,
        {
            "action": "config",
            "configs": config_payload,
        },
    )
    print("[CONFIG RESPONSE]")
    print(json.dumps(config_response, indent=2, ensure_ascii=False))
    cache(task_name=f"{TASK}_config_response", content=config_response)

    final_turbinecheck = run_final_turbinecheck(
        hub=hub,
        start_ts=run_start_ts,
        session_timeout_s=session_timeout_s,
    )
    print("[FINAL TURBINECHECK]")
    print(json.dumps(final_turbinecheck, indent=2, ensure_ascii=False))

    ensure_time_left(run_start_ts, session_timeout_s, extra_margin_s=DONE_MARGIN_S)
    done_response = submit_action(hub, {"action": "done"})
    print("[DONE RESPONSE]")
    print(json.dumps(done_response, indent=2, ensure_ascii=False))
    cache(task_name=f"{TASK}_done_response", content=done_response)


if __name__ == "__main__":
    main()