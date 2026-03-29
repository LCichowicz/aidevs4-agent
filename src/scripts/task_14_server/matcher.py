"""
LLM-based item resolver for the negotiations task.

Flow:
1. Parse the natural-language query with Bielik → JSON list of item descriptions.
2. For each item description, determine its category (first-word bucket) via
   keyword matching against the first_word_index keys.
3. Send Bielik the full list of items in that category and ask it to return
   the exact item code that best matches the description.
4. Return the resolved item codes.
"""

from __future__ import annotations

import json
import re

from src.llm.client import LLMClient


# ---------------------------------------------------------------------------
# Query → item description list
# ---------------------------------------------------------------------------

_PARSE_SYSTEM = (
    "Jesteś asystentem ekstrakcji danych. "
    "Użytkownik poda zapytanie w języku polskim dotyczące potrzebnych przedmiotów. "
    "Wyodrębnij listę potrzebnych przedmiotów i zwróć JSON w formacie:\n"
    '{"items": ["opis przedmiotu 1", "opis przedmiotu 2", ...]}\n'
    "Nie dodawaj żadnego dodatkowego tekstu poza JSON."
)


def parse_query_to_items(query: str, llm: LLMClient) -> list[str]:
    """Return list of item descriptions extracted from natural-language query."""
    messages = [
        {"role": "system", "content": _PARSE_SYSTEM},
        {"role": "user", "content": query},
    ]
    raw = llm.chat(messages)
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        data = json.loads(raw)
        items = data.get("items", [])
        return [str(i) for i in items if i]
    except (json.JSONDecodeError, AttributeError):
        # Fallback: treat whole query as one item
        return [query]


# ---------------------------------------------------------------------------
# Item description → item code
# ---------------------------------------------------------------------------

_CODE_SYSTEM = (
    "Jesteś asystentem doboru przedmiotów elektronicznych. "
    "Dostaniesz opis szukanego przedmiotu i listę dostępnych przedmiotów z kodami. "
    "Wybierz przedmiot który NAJLEPIEJ pasuje do opisu i zwróć TYLKO jego kod w formacie JSON:\n"
    '{"code": "KOD_PRZEDMIOTU"}\n'
    "Nie dodawaj żadnego dodatkowego tekstu."
)


def find_item_code(
    description: str,
    items: list[tuple[str, str]],  # [(code, full_description), ...]
    llm: LLMClient,
) -> str | None:
    """Ask Bielik to pick the best matching item code for *description*."""
    if not items:
        return None

    items_text = "\n".join(f"- {code}: {name}" for code, name in items)
    user_msg = f"Szukany przedmiot: {description}\n\nDostępne przedmioty:\n{items_text}"

    messages = [
        {"role": "system", "content": _CODE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    raw = llm.chat(messages)
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        data = json.loads(raw)
        return str(data.get("code", "")).strip() or None
    except (json.JSONDecodeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Category determination (no LLM needed)
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "do", "dla", "lub", "jak", "ten", "tej", "nie", "ale", "sie",
    "czy", "pod", "nad", "przy", "we", "ze", "na", "po", "za",
    "oraz", "i", "a", "o", "w", "z", "to", "co",
    "potrzebuje", "chce", "szukam", "potrzebujesz",
    "kupic", "nabyc", "zakup",
}


def _keywords(text: str) -> list[str]:
    words = re.findall(r"\b[\w]+\b", text.lower())
    return [w for w in words if len(w) >= 3 and w not in _STOP_WORDS]


def determine_category(description: str, first_word_index: dict) -> str | None:
    """
    Return the first-word category key from first_word_index that best matches
    the item description. Tries exact match first, then 4-char stem match.
    """
    keywords = _keywords(description)
    categories = list(first_word_index.keys())

    # Exact match
    for kw in keywords:
        if kw in first_word_index:
            return kw

    # Stem match (4+ chars prefix)
    for kw in keywords:
        if len(kw) < 4:
            continue
        for cat in categories:
            if cat.startswith(kw[:4]) or kw.startswith(cat[:4]):
                return cat

    return None


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

def resolve_items(
    query: str,
    item_code_to_meta: dict,
    first_word_index: dict,
    llm: LLMClient,
) -> list[str]:
    """
    Parse query, resolve each item to a code, return list of item codes.
    """
    descriptions = parse_query_to_items(query, llm)

    codes: list[str] = []
    for desc in descriptions:
        category = determine_category(desc, first_word_index)
        if category is None:
            continue

        category_codes = first_word_index.get(category, set())
        items_in_category = [
            (code, item_code_to_meta[code]["description"])
            for code in category_codes
            if code in item_code_to_meta
        ]

        code = find_item_code(desc, items_in_category, llm)
        if code and code in item_code_to_meta:
            codes.append(code)

    return codes
