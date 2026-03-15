# TODO:
# payload is currently rendered via LLM directly in this script.
# After finishing course tasks, refactor into:
# loader -> parser -> facts -> renderer -> validator pipeline.

from pathlib import Path
import re
import requests

from PIL import Image, ImageOps
import pytesseract

from src.llm.client import LLMClient
from src.llm.hub_client import HubClient


BASE_URL = "https://hub.ag3nts.org/dane/doc"
CACHE_DIR = Path("cache/doc")

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
BINARY_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}


def build_doc_url(file_name: str) -> str:
    file_name = file_name.lstrip("/")
    return f"{BASE_URL}/{file_name}"


def build_cache_path(file_name: str) -> Path:
    file_name = file_name.lstrip("/")
    cache_path = CACHE_DIR / file_name
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    return cache_path


def is_text_file(file_name: str) -> bool:
    return Path(file_name).suffix.lower() in TEXT_EXTENSIONS


def is_image_file(file_name: str) -> bool:
    return Path(file_name).suffix.lower() in IMAGE_EXTENSIONS


def extract_includes(content: str) -> list[str]:
    return re.findall(r'include file="([^"]+)"', content)


def download_file(file_name: str) -> str | bytes:
    url = build_doc_url(file_name)
    cache_path = build_cache_path(file_name)

    if cache_path.exists():
        print(f"Loading {file_name} from cache")
        if is_text_file(file_name):
            return cache_path.read_text(encoding="utf-8")
        return cache_path.read_bytes()

    print(f"Downloading {file_name} from {url}")
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    if is_text_file(file_name):
        content = response.text
        cache_path.write_text(content, encoding="utf-8")
        return content

    content = response.content
    cache_path.write_bytes(content)
    return content


def read_table_with_tesseract(image_path: str | Path, lang: str = "pol") -> str:
    image_path = Path(image_path)
    image = Image.open(image_path)
    image = ImageOps.grayscale(image)

    text = pytesseract.image_to_string(
        image,
        lang=lang,
        config="--psm 6"
    )
    return text


def load_all_documents() -> tuple[str, dict[str, str], dict[str, str]]:
    """
    Returns:
        index_text,
        text_docs: filename -> text,
        ocr_docs: filename -> OCR text
    """
    index_text = download_file("index.md")
    assert isinstance(index_text, str)
    text_docs: dict[str, str] = {"index.md": index_text}
    ocr_docs: dict[str, str] = {}

    pending = extract_includes(index_text)
    seen = set(["index.md"])

    while pending:
        file_name = pending.pop(0)
        if file_name in seen:
            continue
        seen.add(file_name)

        content = download_file(file_name)

        if is_text_file(file_name):
            assert isinstance(content, str)
            text_docs[file_name] = content

            nested_includes = extract_includes(content)
            for nested in nested_includes:
                if nested not in seen:
                    pending.append(nested)

        else:
            if is_image_file(file_name):
                image_path = build_cache_path(file_name)
                try:
                    ocr_text = read_table_with_tesseract(image_path)
                    ocr_docs[file_name] = ocr_text
                except Exception as exc:
                    print(f"OCR failed for {file_name}: {exc}")

    return index_text, text_docs, ocr_docs


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text).strip()


def find_declaration_template(text_docs: dict[str, str], ocr_docs: dict[str, str]) -> str:
    all_sources: dict[str, str] = {}
    all_sources.update(text_docs)
    all_sources.update({f"OCR::{k}": v for k, v in ocr_docs.items()})

    header = "SYSTEM PRZESYŁEK KONDUKTORSKICH - DEKLARACJA ZAWARTOŚCI"
    end_marker = "BIORĘ NA SIEBIE KONSEKWENCJĘ ZA FAŁSZYWE OŚWIADCZENIE."

    for name, content in all_sources.items():
        text = normalize_whitespace(content)

        if header not in text:
            continue

        start = text.find(header)
        end = text.find(end_marker, start)

        if end == -1:
            continue

        end = end + len(end_marker)

        line_end = text.find("\n", end)
        if line_end == -1:
            line_end = len(text)

        snippet_end = line_end

        rest = text[line_end:].splitlines()
        for line in rest:
            stripped = line.strip()
            if not stripped:
                continue

            if set(stripped) == {"="}:
                snippet_end += len("\n" + line)
            break

        snippet = text[start:snippet_end].strip()

        required_markers = [
            "PUNKT NADAWCZY:",
            "PUNKT DOCELOWY:",
            "TRASA:",
            "KATEGORIA PRZESYŁKI:",
            "OPIS ZAWARTOŚCI",
            "DEKLAROWANA MASA (kg):",
            "WDP:",
            "UWAGI SPECJALNE:",
            "KWOTA DO ZAPŁATY:",
        ]
        if all(marker in snippet for marker in required_markers):
            print(f"Template found in: {name}")
            return snippet

    raise ValueError("Nie udało się odnaleźć wzoru deklaracji w dokumentacji.")


def cleanup_llm_output(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    bad_prefixes = [
        "Oto deklaracja:",
        "Gotowa deklaracja:",
        "Poniżej deklaracja:",
    ]
    for prefix in bad_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    return text


def render_declaration_with_bielik(template_text: str, shipment_data: dict, llm_client: LLMClient) -> str:
    system_prompt = (
        "Jesteś formatterem dokumentów urzędowych. "
        "Masz wyłącznie wypełnić wzór deklaracji na podstawie przekazanych danych. "
        "Nie wolno Ci zmieniać nazw pól, separatorów, kolejności linii ani dopisywać komentarzy. "
        "Masz zwrócić wyłącznie finalny dokument jako czysty tekst."
    )

    user_prompt = f"""
WYPEŁNIJ DOKŁADNIE TEN WZÓR:

{template_text}

DANE DO WSTAWIENIA:
- DATA: {shipment_data["date"]}
- PUNKT NADAWCZY: {shipment_data["source_point"]}
- NADAWCA: {shipment_data["sender_id"]}
- PUNKT DOCELOWY: {shipment_data["destination_point"]}
- TRASA: {shipment_data["route_code"]}
- KATEGORIA PRZESYŁKI: {shipment_data["category"]}
- OPIS ZAWARTOŚCI: {shipment_data["description"]}
- DEKLAROWANA MASA (kg): {shipment_data["weight_kg"]}
- WDP: {shipment_data["wdp"]}
- KWOTA DO ZAPŁATY: {shipment_data["payment_pp"]}

UWAGI SPECJALNE:
To pole ma pozostać puste. Nie wpisuj tam słów "brak", "-", "nie dotyczy" ani niczego podobnego.

ZASADY:
1. Zachowaj dokładnie układ wzoru.
2. Nie zmieniaj nazw pól.
3. Nie dodawaj żadnych komentarzy.
4. Nie używaj markdown ani potrójnych backticków.
5. zachowaj układ linii rozdzielających
6. Zwróć wyłącznie finalny dokument.
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw_response = llm_client.chat(messages)
    declaration = cleanup_llm_output(raw_response)
    return declaration


def validate_required_values(declaration: str, shipment_data: dict) -> None:
    required_lines = [
        f"DATA: {shipment_data['date']}",
        f"PUNKT NADAWCZY: {shipment_data['source_point']}",
        f"NADAWCA: {shipment_data['sender_id']}",
        f"PUNKT DOCELOWY: {shipment_data['destination_point']}",
        f"TRASA: {shipment_data['route_code']}",
        f"KATEGORIA PRZESYŁKI: {shipment_data['category']}",
        f"DEKLAROWANA MASA (kg): {shipment_data['weight_kg']}",
        f"WDP: {shipment_data['wdp']}",
        f"KWOTA DO ZAPŁATY: {shipment_data['payment_pp']}",
    ]

    for line in required_lines:
        if line not in declaration:
            raise ValueError(f"Brakuje wymaganej linii lub ma złą wartość: {line}")

    if shipment_data["description"] not in declaration:
        raise ValueError("Brakuje poprawnego opisu zawartości.")


def validate_special_notes_empty(declaration: str) -> None:
    marker = "UWAGI SPECJALNE:"
    if marker not in declaration:
        raise ValueError("Brakuje sekcji 'UWAGI SPECJALNE:'.")

    after = declaration.split(marker, 1)[1]


    next_separator = "------------------------------------------------------"
    idx = after.find(next_separator)

    if idx == -1:
        raise ValueError("Nie udało się zwalidować sekcji 'UWAGI SPECJALNE:'.")

    notes_body = after[:idx]
    if notes_body.strip():
        raise ValueError(f"Sekcja 'UWAGI SPECJALNE' nie jest pusta: {notes_body!r}")


def validate_declaration(declaration: str, shipment_data: dict) -> None:
    validate_required_values(declaration, shipment_data)
    validate_special_notes_empty(declaration)


def main():
    hub = HubClient()
    llm = LLMClient()

    index_text, text_docs, ocr_docs = load_all_documents()

    # print("=== INDEX ===")
    # print(index_text)

    # print("\n=== TEXT DOCS ===")
    # for name in text_docs:
    #     print("-", name)

    # print("\n=== OCR DOCS ===")
    # for name, text in ocr_docs.items():
    #     print(f"\n--- OCR: {name} ---")
    #     print(text)

    template_text = find_declaration_template(text_docs, ocr_docs)

    print("\n=== TEMPLATE FOUND ===")
    print(template_text)

    shipment_data = {
        "date": "2026-03-15",
        "sender_id": "450202122",
        "source_point": "Gdańsk",
        "destination_point": "Żarnowiec",
        "route_code": "X-01",
        "category": "A",
        "description": "kasety z paliwem do reaktora",
        "weight_kg": 2800,
        "wdp": 4,
        "payment_pp": "0 PP",
    }

    declaration = render_declaration_with_bielik(template_text, shipment_data, llm)

    print("\n=== DECLARATION GENERATED BY BIELIK ===")
    print(declaration)

    validate_declaration(declaration, shipment_data)

    response = hub.submit("sendit", {"declaration": declaration})
    print("\n=== HUB RESPONSE ===")
    print(response)


if __name__ == "__main__":
    main()