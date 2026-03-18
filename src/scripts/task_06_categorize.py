import csv
from dataclasses import dataclass
from typing import Any

from io import StringIO
from src.llm.hub_client import HubClient


TASK_NAME = "categorize"


@dataclass
class Item:
    id: str
    description: str


@dataclass
class AttemptResult:
    success: bool
    flag: str | None
    failed_item_id: str | None
    responses: list[dict[str, Any]]
    error_message: str | None


def parse_items(csv_text: str) -> list[Item]:
    reader = csv.DictReader(StringIO(csv_text))

    items = []
    for row in reader:
        item = Item(
            id=row['code'],
            description = row['description']
        )
        items.append(item)
 
    print(f"Długość listy: {len(items)}")
    return items

def render_prompt(prompt_template: str, item: Item) -> str:

    return prompt_template.format(
        id = item.id,
        description = item.description
        )



def run_attempt(hub: HubClient, items: list[Item], prompt_template: str) -> AttemptResult:
    task = "categorize"
    responses: list[dict[str, Any]] = []

    hub.submit(task=task, answer={"prompt": "reset"})

    for item in items:
        prompt = render_prompt(prompt_template, item)
        print(f"\nITEM: {item.id}")
        print(f"DESC: {item.description}")
        print(f"PROMPT: {prompt}")

        try:
            answer = hub.submit(task=task, answer={"prompt": prompt})
            print(f"ANSWER: {answer}")
            responses.append(answer)


            answer_text = str(answer)
            if "FLG:" in answer_text:
                return AttemptResult(
                    success=True,
                    flag=answer_text,
                    failed_item_id=None,
                    responses=responses,
                    error_message=None,
                )

        except RuntimeError as e:
            print(f"FAILED ON ITEM: {item.id}")
            print(f"ERROR: {e}")

            return AttemptResult(
                success=False,
                flag=None,
                failed_item_id=item.id,
                responses=responses,
                error_message=str(e),
            )

    return AttemptResult(
        success=False,
        flag=None,
        failed_item_id=None,
        responses=responses,
        error_message="Attempt finished without flag",
    )
def reorder_items(items):
    order = "J-D-I-B-A-C-G-E-H-F"
    indices = [ord(letter) - ord('A') for letter in order.split("-")]
    
    return [items[i] for i in indices]


def main() -> None:
    hub = HubClient()

    prompt_template = "Classify item. Reply only DNG for things involving guns, weapons, explosives, toxins, flamable or NEU for the rest. ID:{id} DESC:{description}. Reactor fuel cassette that can be used agian has to be classsified NEU"

    csv_text = hub.download_text(relative_path='categorize.csv')
    items = parse_items(csv_text)
    reordered_items = reorder_items(items)

    for item in reordered_items:
        print(item.id, item.description)

    result = run_attempt(hub, reordered_items, prompt_template)
    print(items)



if __name__ == "__main__":
    main()