
from src.llm.hub_client import HubClient
from src.utils.artifacts import save_task_artifact

TASK = "drone"
POWER_PLANT_CODE = "PWR6132PL"

def build_instructions(col: int, row: int) -> list[str]:
    return [
        f"setDestinationObject({POWER_PLANT_CODE})",
        f"set({col},{row})",
        "set(50m)",
        "set(engineON)",
        "set(100%)",
        "flyToLocation",
    ]


DAM_COL = 2  # manually identified: middle column
DAM_ROW = 4  # manually identified: bottom row

def main() -> None:
    hub = HubClient()

    dam_col, dam_row = DAM_COL, DAM_ROW
    print(f"Dam sector: col={dam_col}, row={dam_row}")

    instructions = build_instructions(dam_col, dam_row)
    answer = {"instructions": instructions}

    print(f"Submitting: {instructions}")
    response = hub.submit_raw(TASK, answer)
    print(f"Response [{response.status_code}]: {response.text}")

    if response.ok:
        data = response.json()
        save_task_artifact(TASK, answer, data)
        if "FLG" in str(data):
            print("FLAG found!")
    else:
        print("Adjust instructions based on error above and re-run.")


if __name__ == "__main__":
    main()
