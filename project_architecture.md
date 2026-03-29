---
name: project_architecture
description: Pełna architektura projektu AI_Devs_4 - agent framework, moduły, dostępne funkcje, skrypty kursowe
type: project
---

# Architektura projektu AI_Devs_4

Projekt to AI agent framework budowany krok po kroku (Day 1–4+) w ramach kursu AI_Devs.
Zadania kursowe rozwiązywane są przez skrypty w `src/scripts/`.
Docelowo funkcje z tych skryptów staną się `Tool` implementacjami wywoływanymi przez agenta.

## Struktura katalogów

```
d:\AI_Devs_4/
├── src/
│   ├── agent/       # Silnik agenta (step, runner, state, plan)
│   ├── cli/         # Interaktywny REPL
│   ├── tools/       # Narzędzia agenta (echo, help, countdown)
│   ├── llm/         # Klienty: LLMClient (Bielik), HubClient (API kursu), ZmailClient (skrzynka)
│   ├── utils/       # Helpery: cache/download, geocoding, artifacts
│   ├── storage/     # Serializacja i zapis tras wykonania
│   ├── scripts/     # Skrypty rozwiązujące zadania kursowe
│   │   ├── task_01_people.py
│   │   ├── task_02_findhim.py
│   │   ├── task_03_registry.py
│   │   ├── task_03_proxy/   # Flask proxy server z LLM orchestratorem
│   │   ├── task_04_sendit.py  # Document ingestion + OCR + deklaracja
│   │   ├── task_05_railway.py  # API sequencing + retry
│   │   ├── task_06_categorize.py  # LLM classification per CSV item
│   │   ├── task_07_electricity.py  # Tile rotation puzzle (3x3 grid)
│   │   ├── task_08_failure.py  # Log parsing + LLM compression
│   │   ├── task_09_mailbox.py  # Inbox scan + fact extraction (date, password, SEC code)
│   │   ├── task_10_drone.py    # Drone navigation + iterative API control (dam sector)
│   │   ├── task_14_negotiations.py  # CSV parsers + hub submission (negotiations)
│   │   ├── task_14_server/          # Flask tool-server: POST /find-cities
│   │   └── task_15_savethem.py      # Grid navigation sequence puzzle
│   └── config.py    # Ładowanie .env.llm
├── cache/           # Pobrane pliki (nie pobieraj ponownie)
│   └── doc/         # Dokumenty z hub.ag3nts.org/dane/doc (task_04)
├── outputs/         # Artefakty zadań ans_{task}.json
├── runs/            # Trace każdego uruchomienia agenta
└── sessions/        # Historia sesji Flask proxy (per sessionID)
```

## Technologie i zależności

- Python 3.12+, biblioteka `openai` (SDK-compatible z NVIDIA API)
- LLM: Bielik 11B v2.6 via NVIDIA integrate API (`speakleash/bielik-11b-v2.6-instruct`)
- Zewnętrzne API: `hub.ag3nts.org` (AI_Devs kurs), Nominatim OSM (geocoding)
- Flask 3.0.3 (web server dla task_03_proxy)
- `pytesseract>=0.3.10` + `Pillow>=10.0.0` (OCR dla task_04_sendit)
- `python-dotenv`, `requests`

## Zmienne środowiskowe (`.env.llm`)

| Zmienna | Wartość/Opis |
|---------|------|
| `BIELIK_API_KEY` | Klucz NVIDIA API |
| `BIELIK_BASE_URL` | `https://integrate.api.nvidia.com/v1` |
| `BIELIK_MODEL` | `speakleash/bielik-11b-v2.6-instruct` |
| `AI_DEVS_API` | Klucz API kursu AI_Devs |
| `AI_DEVS_BASE_URL` | `https://hub.ag3nts.org` |
| `PACKAGES_API_URL` | `https://hub.ag3nts.org/api/packages` (task_03_proxy) |

---

## Moduł: Agent Framework (`src/agent/`)

### src/agent/types.py
- `StepStatus`: `CONTINUE` / `FINAL` / `FAIL` / `NEED_INPUT`
- `AgentInput(task, context, max_steps=10)` — frozen dataclass
- `StepResult(status, tool, tool_input, output, error, message)`
- `AgentOutput(result, status, trace)`

### src/agent/state.py
- `AgentState(steps, notes, run_id)` — mutable runtime state
  - `notes: dict` — working memory dla multi-step tools (np. countdown)

### src/agent/models.py — **STABLE INTERFACE (nie zmieniać)**
- `PlanStep(tool: str, input: dict)`
- `Plan(steps: list[PlanStep])`
- `AgentContext(context: str, user_input: str)`

### src/agent/agent.py
- `parser(task) -> (tool_name, arg)` — parsuje "tool:arg" lub "tool arg"
- `build_tool_input(tool_name, arg) -> dict`
- `Agent.step(agent_input, state) -> StepResult`

### src/agent/runner.py
- `run_agent(agent, agent_input, state) -> AgentOutput` — pętla z max_steps guard

### Przepływ wykonania

```
CLI input: "countdown 3"
  ↓
Agent.step()
  ├─ parser()           → ("countdown", "3")
  ├─ registry.get()     → CountdownTool
  ├─ build_tool_input() → {"n": "3"}
  └─ tool.run(input, state) → StepResult(CONTINUE, message="3")
  ↓
Runner: status == CONTINUE → kolejny krok (max 10)
  ↓
save_trace() → runs/{run_id}.json
```

---

## Moduł: Tools (`src/tools/`)

### src/tools/base.py
- `Tool(name, help)` — klasa bazowa
- `Tool.run(tool_input: dict, state: AgentState) -> StepResult`

### src/tools/registry.py
- `register(tool)`, `get(name)`, `list_tools()`

### Zarejestrowane narzędzia

| Tool | Plik | Opis |
|------|------|------|
| `echo` | `echo.py` | Zwraca podany tekst |
| `tools` | `help.py` | Listuje dostępne narzędzia |
| `countdown` | `countdown.py` | Multi-step odliczanie przez `state.notes` |

---

## Moduł: LLM (`src/llm/`)

### src/llm/zmail_client.py — ZmailClient (API skrzynki mailowej)

| Metoda | Akcja | Opis |
|--------|-------|------|
| `get_inbox(page, perPage)` | `getInbox` | Lista wątków (metadata: subject/from/to/date) |
| `get_thread(thread_id)` | `getThread` | Lista rowID/messageID dla wątku (bez treści) |
| `get_messages(ids)` | `getMessages` | Pełna treść wiadomości po rowID lub messageID |
| `search(query, page, perPage)` | `search` | Wyszukiwanie Gmail-like (from:, subject:, OR, AND) |
| `reset()` | `reset` | Reset licznika requestów w memcache |

### src/llm/client.py — LLMClient (Bielik 11B via NVIDIA)
- `LLMClient.chat(messages) -> str` — temperatura=0
- `LLMClient.chat_json_schema(messages, schema) -> Any` — z JSON schema constraint

### src/llm/hub_client.py — HubClient (API kursu AI_Devs)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| `get_person_locations(name, surname)` | `POST /api/location` | Lokalizacje osoby |
| `get_access_level(name, surname, birth_year)` | `POST /api/accesslevel` | Poziom dostępu |
| `download_text(path)` | `GET /data/{key}/{path}` | Pobierz plik jako tekst |
| `download_text_no_key(path)` | `GET /dane/{path}` | Pobierz plik jako tekst bez klucza API w URL |
| `download_bytes(path)` | `GET /data/{key}/{path}` | Pobierz plik jako bajty |
| `submit(task, answer)` | `POST /verify` | Wyślij odpowiedź; rzuca `RuntimeError` na błąd HTTP |
| `submit_raw(task, answer)` | `POST /verify` | Wyślij odpowiedź; zwraca surowy `Response` (bez rzucania wyjątku) |

---

## Moduł: Utils (`src/utils/`)

### src/utils/download.py
- `get_cached_or_download_text(file_name, hub_client) -> str` — cache w `cache/`
- `get_cached_or_download_text_no_key(file_name, hub_client) -> str` — cache dla plików z `/dane/` (bez klucza API w URL)
- `load_person_locations_with_cache(hub, suspect) -> str` — cache lokalizacji per osoba
- `geocode_city(city) -> (lat, lon)` — Nominatim OSM, szuka w Polsce

### src/utils/artifacts.py
- `save_task_artifact(task_name, answer, response)` — zapisuje do `outputs/ans_{task_name}.json`
- `cache_text(task_name, content)` — zapisuje dowolny JSON do `cache/{task_name}.json`

---

## Moduł: Storage (`src/storage/`)

### src/storage/serializers.py
- `to_json_safe(value) -> Any` — konwertuje dataclasses/enum/pydantic do JSON
- `serialize_step_result(step, step_index) -> dict`

### src/storage/runs.py
- `build_trace_payload(state) -> dict`
- `save_trace(state) -> Path` — zapisuje do `runs/{run_id}.json`

---

## Skrypty zadań (`src/scripts/`)

### task_01_people.py — filtrowanie osób z CSV
Cel: mężczyźni urodzeni w Grudziądzu, wiek 20–40, zawód transport.

| Funkcja | Opis |
|---------|------|
| `parse_people_csv(csv_text)` | Parsuje CSV, dodaje `source_id` |
| `filter_candidates(rows)` | Filtr: płeć M + Grudziądz + wiek 20–40 |
| `build_jobs_batch(candidates)` | Formatuje zawody do promptu LLM |
| `build_tagging_messages(jobs_batch)` | Tworzy system+user messages dla LLM |
| `build_answer(candidates, tags_map)` | Filtruje po tagu `transport` |

### task_02_findhim.py — osoba najbliżej elektrowni atomowej
Cel: znalezienie podejrzanego przebywającego najbliżej elektrowni atomowej.

| Funkcja | Opis |
|---------|------|
| `collect_all_locations(hub, suspects)` | Pobiera lokalizacje każdej osoby (z cache) |
| `parse_power_plants(json_text)` | Parsuje elektrownie + geokoduje miasta |
| `haversine_distance_km(lat1, lon1, lat2, lon2)` | Odległość po powierzchni Ziemi [km] |
| `compute_distances(people, plants)` | Dla każdej osoby: najbliższa elektrownia |
| `find_best_candidate(results)` | Zwraca osobę z najmniejszą odległością |

### task_03_registry.py — prosty test API kursu
Prosty skrypt testujący połączenie z endpointem kursu.

### task_10_drone.py — Nawigacja drona i iteracyjne sterowanie przez API (Day 10)
Cel: zaprogramowanie drona bojowego tak, aby oficjalnie celował w elektrownię (PWR6132PL), ale faktycznie zrzucił ładunek na pobliską tamę.

| Funkcja | Opis |
|---------|------|
| `find_dam_sector(img)` | PIL: dla każdego sektora siatki liczy `mean(B) - mean(R)`; sektor z max wynikiem = tama |
| `_detect_boundaries(values, min_gap)` | Wykrywa ciemne linie siatki po gradiencie jasności; grupuje piksele w klastry |
| `build_instructions(col, row)` | Buduje listę instrukcji: `setDestinationObject → set(x,y) → set(50m) → set(engineON) → set(100%) → set(destroy) → set(return) → flyToLocation` |
| `main()` | Download mapy → detekcja sektora tamy → submit → odczyt odpowiedzi |

**Sektor tamy:** `DAM_COL=2`, `DAM_ROW=4` (siatka 3×4, ręcznie zidentyfikowane).
**Instrukcje odkryte iteracyjnie** na podstawie komunikatów błędów API.
**Submit:** `hub.submit_raw("drone", {"instructions": [...]})`.
**Cache:** `cache/drone.png`.

### task_09_mailbox.py — Przeszukiwanie skrzynki mailowej (Day 9)
Cel: znalezienie daty ataku na elektrownię, hasła do systemu pracowniczego i kodu potwierdzenia z ticketu SEC.

| Funkcja | Opis |
|---------|------|
| `scan_inbox_for_relevant_threads(client)` | Paginuje inbox po metadanych, filtruje wątki wg `INBOX_FILTER` (proton.me, sec-, pwr6132pl, hasło…) |
| `search_for_threads(client, queries)` | Celowane search dla maili niewidocznych w recent inbox (np. stary mail z hasłem) |
| `fetch_messages_for_threads(client, thread_ids)` | Dwuetapowy fetch: `getThread` → `getMessages` z `time.sleep(0.5)` |
| `extract_evidence(messages)` | Regex: SEC kody, daty z kontekstem ataku, hasło z next-line po `hasłem:` |
| `best_password(candidates)` | Wybiera hasło wg score: mixed-case + cyfry + special |

**Submit:** `hub.submit("mailbox", {"password": ..., "date": ..., "confirmation_code": ...})`.

### task_03_proxy/ — Flask proxy server z LLM orchestratorem
Serwer HTTP pośredniczący między operatorem a systemem paczek.
Operator pisze wiadomości w języku naturalnym; LLM decyduje o akcji.

**Uruchomienie:** `python -m src.scripts.task_03_proxy.app` (port 5000)

#### Endpointy Flask (`app.py`)
- `GET /health` → `{"status": "ok"}`
- `POST /` — przyjmuje `{"sessionID": "...", "msg": "..."}`, zwraca `{"msg": "..."}`

#### ProxyOrchestrator (`orchestrator.py`)
Główna logika przetwarzania wiadomości.

| Metoda | Opis |
|--------|------|
| `handle_message(session_id, user_message) -> str` | Główny handler: regex → LLM → tool call |
| `_extract_package_id(text)` | Regex dla wzorca `PKGxxxxxxxx` (8 cyfr) |
| `_decide_next_action(history) -> dict` | Wywołuje LLM, zwraca akcję: `respond` / `check_package` / `redirect_package` |
| `_build_check_reply(package_id, result)` | Formatuje odpowiedź po sprawdzeniu paczki |
| `_build_redirect_reply(package_id, result)` | Formatuje odpowiedź po przekierowaniu |
| `_extract_action_payload(text)` | Parsuje JSON z odpowiedzi LLM (z fallbackiem) |

**Logika decyzyjna:**
1. Jeśli `msg` zawiera `PKGxxxxxxxx` → deterministycznie sprawdź paczkę (lub redirect jeśli LLM zdecydował)
2. W pozostałych przypadkach → LLM decyduje o akcji
3. `REDIRECT_OVERRIDE_DESTINATION = "PWR6132PL"` — stały override miejsca docelowego

#### PackagesClient (`packages_client.py`)
Klient HTTP do `hub.ag3nts.org/api/packages`.

| Metoda | Payload | Opis |
|--------|---------|------|
| `check_package(package_id)` | `{action: "check", packageid: ...}` | Sprawdź status paczki |
| `redirect_package(package_id, destination, code)` | `{action: "redirect", ...}` | Przekieruj paczkę |

#### SessionStore (`session_store.py`)
Persystencja historii rozmów w `sessions/{session_id}.json`.

| Metoda | Opis |
|--------|------|
| `get_history(session_id) -> list[dict]` | Odczytaj historię |
| `append(session_id, role, content)` | Dodaj wiadomość (role: user/assistant) |
| `append_tool_result(session_id, tool_name, result)` | Dodaj wynik narzędzia (role: tool) |

#### ProxyTraceLogger (`trace.py`)
- `log(message, **kwargs)` — loguje przez Python `logging` (logger: `task_03_proxy.trace`)

### task_04_sendit.py — Document ingestion + OCR + deklaracja kolejowa
Cel: załadowanie dokumentacji ze zdalnego serwera, wyekstrahowanie wzoru deklaracji, wypełnienie jej przez LLM i wysłanie do kursu.

| Funkcja | Opis |
|---------|------|
| `download_file(file_name)` | Pobiera plik (tekst lub bajty) z cache lub z `hub.ag3nts.org/dane/doc` |
| `extract_includes(content)` | Regex: wyciąga `include file="..."` z Markdown |
| `read_table_with_tesseract(image_path)` | OCR: PIL grayscale → pytesseract (lang=pol, psm=6) |
| `load_all_documents()` | Rekurencyjny loader: `index.md` → includes → OCR dla obrazów |
| `find_declaration_template(text_docs, ocr_docs)` | Szuka wzoru deklaracji po nagłówku i markerach |
| `render_declaration_with_bielik(template, data, llm)` | Bielik LLM wypełnia wzór danymi przesyłki |
| `cleanup_llm_output(text)` | Usuwa markdown/backticki i złe prefiksy z odpowiedzi LLM |
| `validate_declaration(declaration, data)` | Sprawdza wymagane pola + puste UWAGI SPECJALNE |
| `main()` | Orkiestracja: load → template → render → validate → submit |

**Dane przesyłki (hardcoded w main):** Gdańsk → Żarnowiec, trasa X-01, kasety z paliwem do reaktora.
**Cache:** `cache/doc/` (pliki tekstowe i obrazy).
**Submit:** `hub.submit("sendit", {"declaration": ...})`.

### task_05_railway.py — Rekonfiguracja trasy kolejowej przez API
Cel: otwarcie trasy `X-01` przez sekwencję akcji API z obsługą rate-limiting.

| Funkcja | Opis |
|---------|------|
| `build_railway_steps(route)` | Zwraca listę kroków: `reconfigure → setstatus(RTOPEN) → save` |
| `extract_retry_delay(status_code, body, headers, attempt_no)` | Wylicza czas oczekiwania z `retry_after` w body, nagłówka `Retry-After`, lub eksponencjalnego fallbacku dla 503 |
| `parse_response_body(response)` | Parsuje JSON lub zwraca `{"raw_text": ...}` |
| `submit_with_retry(hub, task, answer, max_retries)` | Pętla retry dla 429/503; rzuca `RuntimeError` na inne statusy |
| `run_railway_flow(hub, route)` | Wykonuje kolejno wszystkie kroki dla podanej trasy |

**Submit:** `hub.submit_raw("railway", step)` — surowa odpowiedź HTTP.

### task_06_categorize.py — Kategoryzacja pozycji przez LLM
Cel: sklasyfikowanie każdej pozycji z CSV jako `DNG` (niebezpieczna) lub `NEU` (neutralna).

| Funkcja / klasa | Opis |
|-----------------|------|
| `Item` | Dataclass: `id` (kod pozycji), `description` |
| `AttemptResult` | Dataclass: wynik próby — flaga, błąd, lista odpowiedzi |
| `parse_items(csv_text)` | Parsuje CSV z kolumnami `code`, `description` |
| `render_prompt(prompt_template, item)` | Formatuje prompt z `{id}` i `{description}` |
| `reorder_items(items)` | Przeporządkowuje listę wg zakodowanej kolejności `J-D-I-B-A-C-G-E-H-F` |
| `run_attempt(hub, items, prompt_template)` | Reset → iteruje pozycje → submit prompt per item; przerywa przy fladze lub błędzie |

**Dane wejściowe:** `hub.download_text("categorize.csv")`.
**Submit per pozycja:** `hub.submit("categorize", {"prompt": prompt})`.
**Reset sesji:** `hub.submit("categorize", {"prompt": "reset"})` przed każdą próbą.

### task_07_electricity.py — Rotacja kafelków w puzzlu obwodu elektrycznego
Cel: ułożenie puzzla siatki 3×3 z kafelkami obwodu przez sekwencję rotacji wysyłanych do API kursu.

| Funkcja | Opis |
|---------|------|
| `execute_rotation_plan(hub)` | Iteruje `ROTATION_PLAN` i wysyła `hub.submit("electricity", {"rotate": "RxC"})` dla każdej niezerowej rotacji |
| `get_cached_bytes(file_name, download_func)` | Cache binarny w `cache/`; pobiera przez `download_func()` gdy brak pliku |
| `download_current_board(hub)` | Pobiera `electricity.png` przez `hub.download_bytes()` |
| `download_solved_board()` | Pobiera referencyjny obraz rozwiązania |
| `main()` | Reset planszy → download obu obrazów → `execute_rotation_plan` |

**`ROTATION_PLAN`:** hardcoded dict `"RxC" → liczba rotacji 90°` dla siatki 3×3.
**Reset:** `GET /data/{key}/electricity.png?reset=1` przed każdym uruchomieniem.
**Submit:** `hub.submit("electricity", {"rotate": "RxC"})`.
**Cache:** `cache/electricity.png`, `cache/solved_electricity.png`.

### task_14_negotiations.py + task_14_server/ — Serwer narzędzi negocjacyjnych (Day 13)
Cel: wystawienie endpointu `POST /find-cities` (Flask + ngrok) dla agenta kursu, który szuka miast sprzedających komponenty do turbiny wiatrowej.

**Parsery CSV (`task_14_negotiations.py`):**

| Funkcja | Opis |
|---------|------|
| `parse_items(item_csv)` | Parsuje CSV przedmiotów → `{code: {description, first_word}}` + set kategorii |
| `parse_connections(connections_csv)` | `{item_code: set(city_codes)}` |
| `parse_cities(cities_csv)` | `{city_code: name}` |
| `build_first_word_index(item_code_to_meta)` | `{first_word_lower: set(item_codes)}` — indeks kategorii |
| `submit_tools(ngrok_base_url)` | Rejestruje URL narzędzia w hubie |
| `check_result()` | Polling huba dla wyniku weryfikacji |

**Serwer Flask (`task_14_server/`):**

| Plik | Opis |
|------|------|
| `app.py` | `POST /find-cities`: `{"params": query}` → `{"output": "Miasto1,Miasto2,..."}` |
| `matcher.py` | `resolve_items()`: Bielik parsuje query → opisy → kategoria → kod; `determine_category()` via keyword match; `find_item_code()` via LLM |
| `data_store.py` | `load_all()`: ładuje CSVs z huba przez `get_cached_or_download_text_no_key` |

**Submit:** `{"tools": [{"URL": "<ngrok>/find-cities", "description": "..."}]}` + polling `{"action": "check"}`.
**Flagi:** zapisane w `outputs/ans_task_14_negotiations.json`.

### task_15_savethem.py — Nawigacja po siatce (Day 14)
Cel: uratowanie uwięzionych pracowników przez przesłanie sekwencji ruchów po siatce.

| Krok | Opis |
|------|------|
| Query `books` | Odpytuje `POST hub/api/books` z `{"query": "fuel efficiency"}` (eksploracja) |
| Submit | `hub.submit("savethem", ["rocket","up","up","up","up","up","up","right","right","right","dismount","right","right","right"])` |

Sekwencja odkryta iteracyjnie; odpowiedź to lista stringów (nie dict).
**Flaga:** zapisana w `outputs/ans_task_15_savethem.json`.

### task_08_failure.py — Analiza logów awarii elektrowni atomowej
Cel: pobranie pliku logów, wyfiltrowanie zdarzeń CRIT, skompresowanie komunikatów przez LLM i wysłanie skróconego logu do kursu.

| Funkcja | Opis |
|---------|------|
| `parse_timestamp(ts_raw)` | Parsuje timestamp `YYYY-MM-DD HH:MM:SS` → `(date_str, time_str)` |
| `parse_log_line(line)` | Regex parsuje linię `[timestamp] [LEVEL] message` → dict lub `None` |
| `msg_extract(message, llm)` | Bielik LLM kompresuje komunikat do jednej linii (zachowując oryginalne znaczenie i nazwy komponentów) |
| `merge_msg(crit_events, crit_msgs)` | Podmienia oryginalne komunikaty skompresowanymi wersjami |
| `render_log(list_of_events)` | Deduplikuje po `message` i renderuje log jako string |

**Dane wejściowe:** `failure.log` pobrany przez `hub.download_text()` z cache.
**Cache pośredni:** `cache/failure_crit.json` (skompresowane komunikaty CRIT), `cache/log_clean.json` (finalny log).
**Submit:** `hub.submit("failure", {"logs": log})`.

---

## Plan docelowy: skrypty → tools

```
src/scripts/task_XX.py     →  src/tools/tool_XX.py
monolityczny main()        →  małe Tool.run(input, state) → StepResult
wywoływany ręcznie z CLI   →  wywoływany przez LLM jako function call
```

Każda funkcja biznesowa (geocoding, distance calc, location lookup, package check) staje się
osobnym `Tool` z jasnym `dict` wejściem — LLM może je komponować przez `Plan(steps=[...])`.
