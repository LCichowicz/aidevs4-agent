from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from src.llm.hub_client import HubClient
from src.llm.zmail_client import ZmailClient
from src.utils.artifacts import save_task_artifact

DELAY = 0.5

FULL_CONFIRMATION_CODE_RE = re.compile(r"\bSEC-[A-Za-z0-9]{32}\b")
SHORT_TICKET_RE = re.compile(r"\bSEC-\d+\b")
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")

# Keywords matched against inbox item metadata (subject/from/to) to select relevant threads
INBOX_FILTER = ["proton.me", "sec-", "pwr6132pl", "hasło", "hasłem", "system pracowniczy", "wiktor", "borkowski"]

# Targeted searches for things that may not appear in recent inbox metadata (e.g. old password email)
TARGETED_SEARCHES = ["from:proton.me", "system pracowniczy"]

PASSWORD_CONTEXT_KEYWORDS = ["hasło", "hasłem", "hasła", "password", "nowe hasło", "system pracowniczy", "credentials"]

DATE_CONTEXT_KEYWORDS = ["zajmie się tym tematem", "dział bezpieczeństwa", "zostanie zniszczony", "atak", "security"]

PASSWORD_STOPWORDS = {
    "hasło", "password", "temporary", "new", "nowe", "login",
    "system", "pracowniczy", "credentials", "twoje", "twój",
    "to", "jest", "dla", "konto", "użytkownika", "uzytkownika", "operator04227",
}


@dataclass
class Facts:
    date: str | None = None
    password: str | None = None
    confirmation_code: str | None = None

    def complete(self) -> bool:
        return all([self.date, self.password, self.confirmation_code])


@dataclass
class Evidence:
    short_tickets: set[str] = field(default_factory=set)
    full_codes: set[str] = field(default_factory=set)
    dates: set[str] = field(default_factory=set)
    passwords: set[str] = field(default_factory=set)


def _is_relevant(item: dict[str, Any]) -> bool:
    combined = " ".join([
        item.get("from", ""), item.get("to", ""), item.get("subject", ""),
    ]).lower()
    return any(kw in combined for kw in INBOX_FILTER)


def scan_inbox_for_relevant_threads(client: ZmailClient) -> set[int]:
    """Page through inbox metadata and collect only relevant thread IDs."""
    thread_ids: set[int] = set()
    page, known_total = 1, 1
    while page <= known_total:
        resp = client.get_inbox(page=page, perPage=20)
        known_total = max(known_total, resp.get("pagination", {}).get("totalPages", 1))
        for item in resp.get("items", []):
            if _is_relevant(item) and isinstance(item.get("threadID"), int):
                thread_ids.add(item["threadID"])
        page += 1
        time.sleep(DELAY)
    return thread_ids


def search_for_threads(client: ZmailClient, queries: list[str]) -> set[int]:
    thread_ids: set[int] = set()
    for query in queries:
        resp = client.search(query=query, page=1, perPage=20)
        for item in resp.get("items", []):
            if isinstance(item.get("threadID"), int):
                thread_ids.add(item["threadID"])
        time.sleep(DELAY)
    return thread_ids


def fetch_messages_for_threads(client: ZmailClient, thread_ids: set[int]) -> list[dict[str, Any]]:
    all_messages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tid in sorted(thread_ids):
        try:
            items = client.get_thread(tid).get("items", [])
            time.sleep(DELAY)
            ids = [item.get("messageID") or item.get("rowID") for item in items if isinstance(item, dict)]
            ids = [i for i in ids if i and i not in seen]
            if not ids:
                continue
            for msg in client.get_messages(ids).get("items", []):
                mid = msg.get("messageID")
                if mid and mid not in seen:
                    seen.add(mid)
                    all_messages.append(msg)
            time.sleep(DELAY)
        except Exception as exc:
            print(f"[WARN] thread {tid}: {exc}")
    return all_messages


def get_text(msg: dict[str, Any]) -> str:
    return "\n".join([
        f"SUBJECT: {msg.get('subject', '')}",
        f"FROM: {msg.get('from', '')}",
        f"TO: {msg.get('to', '')}",
        "",
        str(msg.get("message", "")),
    ]).strip()


def clean(token: str) -> str:
    return token.strip().strip('"\':;,.()[]{}<>')


def is_password_like(token: str) -> bool:
    t = clean(token)
    return (
        len(t) >= 6
        and "@" not in t
        and t.lower() not in PASSWORD_STOPWORDS
        and not DATE_RE.fullmatch(t)
        and not SHORT_TICKET_RE.fullmatch(t)
        and not FULL_CONFIRMATION_CODE_RE.fullmatch(t)
    )


def extract_evidence(messages: list[dict[str, Any]]) -> Evidence:
    ev = Evidence()
    for msg in messages:
        text = get_text(msg)
        body = msg.get("message", "")
        body_lower = body.lower()

        ev.full_codes.update(FULL_CONFIRMATION_CODE_RE.findall(text))
        ev.short_tickets.update(SHORT_TICKET_RE.findall(text))

        dates_in_body = DATE_RE.findall(body)
        if dates_in_body and any(kw in body_lower for kw in DATE_CONTEXT_KEYWORDS):
            ev.dates.update(dates_in_body)

        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not any(kw in line.lower() for kw in PASSWORD_CONTEXT_KEYWORDS):
                continue
            if ":" in line:
                right = line.split(":", 1)[1].strip()
                token = clean(right.split()[0]) if right else ""
                if token and is_password_like(token):
                    ev.passwords.add(token)
            if i + 1 < len(lines):
                nxt = clean(lines[i + 1].strip())
                if nxt and " " not in nxt and is_password_like(nxt):
                    ev.passwords.add(nxt)
    return ev


def best_password(candidates: set[str]) -> str | None:
    if not candidates:
        return None

    def score(t: str) -> tuple[int, int]:
        return (
            int(any(c.islower() for c in t) and any(c.isupper() for c in t))
            + int(any(c.isdigit() for c in t))
            + int(any(not c.isalnum() for c in t)),
            len(t),
        )

    return sorted(candidates, key=score, reverse=True)[0]


def main() -> None:
    client = ZmailClient()
    hub = HubClient()

    # Step 1: scan inbox metadata → pick relevant threads
    thread_ids = scan_inbox_for_relevant_threads(client)

    # Step 2: targeted searches for items unlikely to appear in recent inbox (old password email etc.)
    thread_ids |= search_for_threads(client, TARGETED_SEARCHES)

    # Step 3: fetch full messages only for relevant threads
    messages = fetch_messages_for_threads(client, thread_ids)
    ev = extract_evidence(messages)

    # Step 4: if we found a short ticket but no full code, search specifically for that thread
    if ev.short_tickets and not ev.full_codes:
        extra = search_for_threads(client, list(ev.short_tickets)) - thread_ids
        if extra:
            ev2 = extract_evidence(fetch_messages_for_threads(client, extra))
            ev.full_codes |= ev2.full_codes
            ev.dates |= ev2.dates
            ev.passwords |= ev2.passwords

    facts = Facts(
        date=sorted(ev.dates)[0] if ev.dates else None,
        password=best_password(ev.passwords),
        confirmation_code=sorted(ev.full_codes)[0] if ev.full_codes else None,
    )

    print(f"date:              {facts.date}")
    print(f"password:          {facts.password}")
    print(f"confirmation_code: {facts.confirmation_code}")

    if not facts.complete():
        raise RuntimeError(f"Incomplete facts: {facts}")

    answer = {"password": facts.password, "date": facts.date, "confirmation_code": facts.confirmation_code}
    response = hub.submit("mailbox", answer)
    save_task_artifact("task_09_mailbox", answer, response)
    print(response)


if __name__ == "__main__":
    main()
