# Architektura AI_Devs_4

## Obecny stan: dwie warstwy

### 1. Agent Framework (`src/agent/`, `src/tools/`) — gotowy silnik

| Komponent | Plik | Rola |
|-----------|------|------|
| `Agent.step()` | `src/agent/agent.py` | Wybiera tool i go wywołuje |
| `Runner.run_agent()` | `src/agent/runner.py` | Pętla wykonania z max_steps guard |
| `AgentState` | `src/agent/state.py` | Mutable runtime state + working memory (`notes`) |
| `StepResult`, `AgentInput`, `AgentOutput` | `src/agent/types.py` | Typy danych |
| `Plan`, `PlanStep`, `AgentContext` | `src/agent/models.py` | **STABLE INTERFACE** — modele planowania |
| `Tool.run(input, state)` | `src/tools/base.py` | Interfejs każdego narzędzia |
| `register`, `get`, `list_tools` | `src/tools/registry.py` | Rejestr narzędzi |
| `save_trace()` | `src/storage/runs.py` | Zapis JSON każdego runu do `runs/` |

#### Aktywne tools

| Tool | Plik | Opis |
|------|------|------|
| `echo` | `src/tools/echo.py` | Zwraca podany tekst |
| `tools` | `src/tools/help.py` | Listuje dostępne narzędzia |
| `countdown` | `src/tools/countdown.py` | Multi-step odliczanie przez `state.notes` |

#### Przepływ wykonania

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

#### StepStatus

```
CONTINUE   → wykonaj kolejny krok
FINAL      → zakończ z sukcesem
FAIL       → zakończ z błędem
NEED_INPUT → czekaj na input użytkownika
```

---

### 2. Skrypty zadań kursowych (`src/scripts/`) — poza agentem

Skrypty rozwiązują konkretne zadania kursowe. Docelowo funkcje z nich trafią do `src/tools/`.

#### task_01_people.py — filtrowanie osób

Cel: znalezienie mężczyzn urodzonych w Grudziądzu, wiek 20–40, zawód transport.

| Funkcja | Opis |
|---------|------|
| `parse_people_csv(csv_text)` | Parsuje CSV, dodaje `source_id` |
| `filter_candidates(rows)` | Filtr: płeć M + Grudziądz + wiek 20–40 |
| `build_jobs_batch(candidates)` | Formatuje zawody do promptu LLM |
| `build_tagging_messages(jobs_batch)` | Tworzy system+user messages dla LLM |
| `build_answer(candidates, tags_map)` | Filtruje po tagu `transport` |

#### task_02_findhim.py — osoba najbliżej elektrowni

Cel: znalezienie podejrzanego przebywającego najbliżej elektrowni atomowej.

| Funkcja | Opis |
|---------|------|
| `collect_all_locations(hub, suspects)` | Pobiera lokalizacje każdej osoby (z cache) |
| `parse_power_plants(json_text)` | Parsuje elektrownie + geokoduje miasta |
| `haversine_distance_km(lat1, lon1, lat2, lon2)` | Odległość po powierzchni Ziemi [km] |
| `compute_distances(people, plants)` | Dla każdej osoby: najbliższa elektrownia |
| `find_best_candidate(results)` | Zwraca osobę z najmniejszą odległością |

#### task_03_registry.py — prosty test API kursu

Skrypt testujący połączenie z endpointem kursu.

#### task_04_sendit.py — Document ingestion + OCR + deklaracja kolejowa (Day 5)

Cel: załadowanie dokumentacji zdalnej, wyekstrahowanie wzoru deklaracji przesyłki, wypełnienie przez LLM i przesłanie do kursu.

| Funkcja | Opis |
|---------|------|
| `download_file(file_name)` | Pobiera plik z cache lub z `hub.ag3nts.org/dane/doc` (tekst lub bajty) |
| `extract_includes(content)` | Regex: wyciąga nazwy plików z `include file="..."` w Markdown |
| `read_table_with_tesseract(image_path)` | OCR: PIL grayscale + pytesseract (lang=pol, psm=6) |
| `load_all_documents()` | Rekurencyjny loader: `index.md` → includes → OCR dla obrazów |
| `find_declaration_template(text_docs, ocr_docs)` | Szuka wzoru deklaracji po nagłówku i zestawie markerów pól |
| `render_declaration_with_bielik(template, data, llm)` | Bielik LLM wypełnia wzór na podstawie dict z danymi przesyłki |
| `cleanup_llm_output(text)` | Usuwa markdown (backticki) i złe prefiksy z odpowiedzi LLM |
| `validate_declaration(declaration, data)` | Sprawdza wymagane pola + że UWAGI SPECJALNE są puste |
| `main()` | Orkiestracja: load → template → render → validate → submit |

**Cache:** `cache/doc/` (pliki tekstowe i obrazy z remote docs).
**Submit:** `hub.submit("sendit", {"declaration": ...})`.
**Nowe zależności:** `pytesseract>=0.3.10`, `Pillow>=10.0.0`.

#### task_05_railway.py — Rekonfiguracja trasy kolejowej przez API (Day 6)

Cel: otwarcie trasy kolejowej `X-01` przez sekwencję akcji API z obsługą rate-limiting.

| Funkcja | Opis |
|---------|------|
| `build_railway_steps(route)` | Zwraca listę kroków: `reconfigure → setstatus(RTOPEN) → save` |
| `extract_retry_delay(status_code, body, headers, attempt_no)` | Wylicza czas oczekiwania z `retry_after` w body, nagłówka `Retry-After`, lub eksponencjalnego fallbacku dla 503 |
| `parse_response_body(response)` | Parsuje JSON lub zwraca `{"raw_text": ...}` |
| `submit_with_retry(hub, task, answer, max_retries)` | Pętla retry dla 429/503 z automatycznym delay; rzuca `RuntimeError` na inne statusy |
| `run_railway_flow(hub, route)` | Wykonuje kolejno wszystkie kroki dla podanej trasy |

**Submit:** `hub.submit_raw("railway", step)` — używa surowej odpowiedzi HTTP (bez rzucania wyjątku na błędny status).

#### task_06_categorize.py — Kategoryzacja pozycji przez LLM (Day 6)

Cel: sklasyfikowanie każdej pozycji z CSV jako `DNG` (niebezpieczna) lub `NEU` (neutralna) i uzyskanie flagi od kursu.

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

#### task_07_electricity.py — Rotacja kafelków w puzzlu obwodu elektrycznego (Day 7)

Cel: ułożenie puzzla siatki 3×3 z kafelkami obwodu przez sekwencję rotacji wysyłanych do API kursu.

| Funkcja | Opis |
|---------|------|
| `execute_rotation_plan(hub)` | Iteruje `ROTATION_PLAN` i wysyła `hub.submit("electricity", {"rotate": "RxC"})` dla każdej niezerowej rotacji |
| `get_cached_bytes(file_name, download_func)` | Cache binarny w `cache/`; pobiera przez `download_func()` gdy brak pliku |
| `download_current_board(hub)` | Pobiera `electricity.png` przez `hub.download_bytes()` |
| `download_solved_board()` | Pobiera referencyjny obraz rozwiązania z `hub.ag3nts.org/i/solved_electricity.png` |
| `load_image_from_bytes(image_bytes)` | Otwiera obraz PIL z `BytesIO` |
| `main()` | Reset planszy (GET RESET_URL) → download obu obrazów → `execute_rotation_plan` |

**`ROTATION_PLAN`:** hardcoded dict `"RxC" → liczba rotacji 90°` dla siatki 3×3.
**Reset:** `GET /data/{key}/electricity.png?reset=1` przed każdym uruchomieniem.
**Submit:** `hub.submit("electricity", {"rotate": "RxC"})` — jedna rotacja o 90° zgodnie z ruchem wskazówek.
**Cache:** `cache/electricity.png`, `cache/solved_electricity.png`.

#### task_09_mailbox.py — Przeszukiwanie skrzynki mailowej (Day 9)

Cel: znalezienie daty ataku na elektrownię, hasła do systemu pracowniczego i kodu potwierdzenia z ticketu bezpieczeństwa.

| Funkcja | Opis |
|---------|------|
| `scan_inbox_for_relevant_threads(client)` | Paginuje inbox po metadanych (subject/from/to), filtruje wątki dopasowane do `INBOX_FILTER` |
| `search_for_threads(client, queries)` | Uruchamia celowane zapytania search (np. dla starych maili niewidocznych w nagłówkach inboxa) |
| `fetch_messages_for_threads(client, thread_ids)` | Dwuetapowy fetch: `getThread` (IDs) → `getMessages` (pełna treść) |
| `extract_evidence(messages)` | Regex: kody `SEC-+32`, krótkie tickety, daty z kontekstem, hasło z next-line po `hasłem:` |
| `best_password(candidates)` | Wybiera hasło z najwyższym score (mixed-case + cyfry + special) |

**Klient:** `ZmailClient` (`src/llm/zmail_client.py`) — POST `/api/zmail`, akcje: `getInbox`, `getThread`, `getMessages`, `search`, `reset`.
**Rate limiting:** `time.sleep(0.5)` po każdym wywołaniu API.
**Submit:** `hub.submit("mailbox", {"password": ..., "date": ..., "confirmation_code": ...})`.

#### task_08_failure.py — Analiza logów awarii elektrowni atomowej (Day 8)

Cel: pobranie pliku logów, wyfiltrowanie zdarzeń CRIT, skompresowanie komunikatów przez LLM i wysłanie skróconego logu do kursu.

| Funkcja | Opis |
|---------|------|
| `parse_timestamp(ts_raw)` | Parsuje timestamp `YYYY-MM-DD HH:MM:SS` → `(date_str, time_str)` |
| `parse_log_line(line)` | Regex parsuje linię `[timestamp] [LEVEL] message` → dict lub `None` |
| `msg_extract(message, llm)` | Bielik LLM kompresuje komunikat do jednej linii (zachowując oryginalne znaczenie i nazwy komponentów) |
| `merge_msg(crit_events, crit_msgs)` | Podmienia oryginalne komunikaty skompresowanymi wersjami |
| `render_log(list_of_events)` | Deduplikuje po `message` i renderuje log jako string |

**Dane wejściowe:** `failure.log` pobrany przez `hub.download_text()`.
**Cache pośredni:** `cache/failure_crit.json` (skompresowane komunikaty CRIT), `cache/log_clean.json` (finalny log).
**Submit:** `hub.submit("failure", {"logs": log})`.

#### task_10_drone.py — Nawigacja drona i iteracyjne sterowanie przez API (Day 10)

Cel: zaprogramowanie drona bojowego tak, aby oficjalnie celował w elektrownię (PWR6132PL), ale faktycznie zrzucił ładunek na pobliską tamę.

| Funkcja | Opis |
|---------|------|
| `find_dam_sector(img)` | PIL: dla każdego sektora siatki liczy `mean(B) - mean(R)`; sektor z max wynikiem = tama |
| `_detect_boundaries(values, min_gap)` | Wykrywa ciemne linie siatki po gradiencie jasności; grupuje piksele w klastry |
| `build_instructions(col, row)` | Buduje listę instrukcji drona: `setDestinationObject → set(x,y) → set(50m) → set(engineON) → set(100%) → set(destroy) → set(return) → flyToLocation` |
| `main()` | Download mapy → detekcja sektora tamy → submit do `/verify` → odczyt odpowiedzi |

**Sektor tamy:** `DAM_COL=2`, `DAM_ROW=4` (siatka 3×4, ręcznie zidentyfikowane).
**Instrukcje odkryte iteracyjnie** na podstawie komunikatów błędów API (zbyt mała wysokość, brak mocy, brak powrotu).
**Submit:** `hub.submit_raw("drone", {"instructions": [...]})` — surowa odpowiedź dla obsługi błędów.
**Cache:** `cache/drone.png`.

#### task_11_evaluation.py — Walidacja danych sensorów i klasyfikacja przez LLM (Day 11)

Cel: walidacja odczytów z 3100+ plików sensorów i klasyfikacja notatek operatora przez LLM w celu wykrycia anomalii.

| Funkcja | Opis |
|---------|------|
| `validate_sensor_data(data)` | Sprawdza zakresy: `temperature_K` (553–873), `pressure_bar` (60–160), `water_level_meters` (5.0–15.0), `voltage_supply_v` (229.0–231.0), `humidity_percent` (40.0–80.0) |
| `build_records_from_sensor_files(sensors_dir)` | Buduje rekordy z `cache/sensors/*.json` |
| `normalize_note(note)` | Lowercase, trim, deduplikuje spacje |
| `build_notes_index(records)` | Indeks unikalnych notatek z deduplication |
| `chunk_list(items, batch_size)` | Dzieli na batche do LLM |
| `classify_notes_batch(llm, notes_batch)` | Bielik klasyfikuje batch notatek: `OK` / `PROBLEM` / `UNKNOWN` |
| `classify_all_notes(llm, notes_index, batch_size)` | Klasyfikuje wszystkie unikalne notatki |
| `find_recheck_file_ids(records, note_labels)` | Znajduje ID plików sensorów z anomaliami |
| `save_local_result(recheck_ids, path)` | Zapisuje `cache/evaluation_recheck.json` |

**Typy sensorów:** `voltage` i `water`; sensory nieaktywne mają zerowe pola poza specyficznymi dla typu.
**Dane wejściowe:** `cache/sensors/0001.json` … `XXXX.json` (łącznie ~3100 plików).
**Submit:** `hub.submit("evaluation", {"recheck": [...]})`.

#### task_12_firmware.py — Zdalne uruchamianie firmware przez shell (Day 12)

Cel: wykonanie `cooler.bin` na zdalnej maszynie wirtualnej po naprawieniu konfiguracji i usunięciu blokady.

| Funkcja | Opis |
|---------|------|
| `get_gitignore(shell)` | Czyta `.gitignore` (forbidden files list) |
| `find_password(shell)` | Czyta hasło z `/home/operator/notes/pass.txt` |
| `read_settings(shell)` | Czyta `settings.ini` |
| `fix_settings(shell, lines)` | Patching: uncomment `SAFETY_CHECK=pass`, ustaw `test_mode.enabled=false`, `cooling.enabled=true` |
| `remove_lock(shell)` | Usuwa `cooler-is-blocked.lock` |
| `run_binary(shell, password)` | Uruchamia `cooler.bin` z hasłem, ekstrahuje `ECCS-[0-9a-f]+` |
| `main()` | Sekwencja: gitignore → hasło → settings → patch → usuń lock → uruchom → submit |

**Ścieżki (hardcoded):** `FIRMWARE_DIR=/opt/firmware/cooler`, `PASS_FILE=/home/operator/notes/pass.txt`.
**Klient:** `ShellClient` z auto-retry (ban/rate-limit/unavailable).
**Submit:** `hub.submit("firmware", {"code": "ECCS-..."})`.

#### task_03_proxy/ — Flask proxy server z LLM orchestratorem

Serwer HTTP pośredniczący między operatorem a systemem paczek.
Operator pisze wiadomości w języku naturalnym; LLM decyduje o akcji.

**Uruchomienie:** `python -m src.scripts.task_03_proxy.app` (port 5000)

##### Endpointy Flask (`app.py`)

- `GET /health` → `{"status": "ok"}`
- `POST /` — przyjmuje `{"sessionID": "...", "msg": "..."}`, zwraca `{"msg": "..."}`

##### ProxyOrchestrator (`orchestrator.py`)

| Metoda | Opis |
|--------|------|
| `handle_message(session_id, user_message) -> str` | Główny handler: regex → LLM → tool call |
| `_extract_package_id(text)` | Regex dla wzorca `PKGxxxxxxxx` (8 cyfr) |
| `_decide_next_action(history) -> dict` | Wywołuje LLM, zwraca akcję JSON |
| `_build_check_reply(package_id, result)` | Formatuje odpowiedź po sprawdzeniu paczki |
| `_build_redirect_reply(package_id, result)` | Formatuje odpowiedź po przekierowaniu |
| `_extract_action_payload(text)` | Parsuje JSON z odpowiedzi LLM (z fallbackiem) |

Możliwe akcje LLM:

```json
{"action": "respond", "message": "tekst"}
{"action": "check_package", "package_id": "PKG12345678"}
{"action": "redirect_package", "package_id": "PKG12345678", "destination": "PWR1234PL", "code": "ABC123"}
```

`REDIRECT_OVERRIDE_DESTINATION = "PWR6132PL"` — stały override miejsca docelowego.

##### PackagesClient (`packages_client.py`)

Klient HTTP do `hub.ag3nts.org/api/packages`.

| Metoda | Opis |
|--------|------|
| `check_package(package_id)` | `action: "check"` — sprawdź status paczki |
| `redirect_package(package_id, destination, code)` | `action: "redirect"` — przekieruj paczkę |

##### SessionStore (`session_store.py`)

Persystencja historii rozmów w `sessions/{session_id}.json`.

| Metoda | Opis |
|--------|------|
| `get_history(session_id) -> list[dict]` | Odczytaj historię |
| `append(session_id, role, content)` | Dodaj wiadomość (role: user/assistant) |
| `append_tool_result(session_id, tool_name, result)` | Dodaj wynik narzędzia (role: tool) |

##### ProxyTraceLogger (`trace.py`)

- `log(message, **kwargs)` — loguje przez Python `logging` (logger: `task_03_proxy.trace`)

---

### 3. Warstwa wspólna (`src/llm/`, `src/utils/`)

#### ZmailClient (`src/llm/zmail_client.py`) — API skrzynki mailowej

| Metoda | Akcja | Opis |
|--------|-------|------|
| `get_inbox(page, perPage)` | `getInbox` | Lista wątków (metadata: subject/from/to/date) |
| `get_thread(thread_id)` | `getThread` | Lista rowID/messageID dla wątku (bez treści) |
| `get_messages(ids)` | `getMessages` | Pełna treść wiadomości po rowID lub messageID |
| `search(query, page, perPage)` | `search` | Wyszukiwanie z operatorami Gmail (from:, subject:, OR, AND) |
| `reset()` | `reset` | Reset licznika requestów w memcache |

#### ShellClient (`src/llm/shell_client.py`) — zdalne wykonywanie poleceń shell

| Metoda                               | Opis                                                                         |
|--------------------------------------|------------------------------------------------------------------------------|
| `run(cmd: str) -> dict`              | Pojedyncze wykonanie polecenia shell przez `POST /api/shell`                 |
| `run_with_retry(cmd, retries, wait)` | Automatyczne ponowienia przy 403 (ban), 429 (rate limit), 503 (unavailable) |

Endpoint: `https://hub.ag3nts.org/api/shell`. Obsługuje `ban_duration` z body odpowiedzi 403.

#### LLMClient (`src/llm/client.py`) — Bielik 11B via NVIDIA API

| Metoda                                              | Opis                                                                              |
|-----------------------------------------------------|-----------------------------------------------------------------------------------|
| `chat(messages) -> str`                             | Zwykłe zapytanie, temperatura=0                                                   |
| `chat_json_schema(messages, schema, schema_name)`   | Odpowiedź zgodna ze schematem JSON; `strict: True`, opcjonalna nazwa schematu     |

#### HubClient (`src/llm/hub_client.py`) — API kursu AI_Devs

| Metoda | Endpoint | Opis |
|--------|----------|------|
| `get_person_locations(name, surname)` | `POST /api/location` | Lokalizacje osoby |
| `get_access_level(name, surname, birth_year)` | `POST /api/accesslevel` | Poziom dostępu |
| `download_text(path)` | `GET /data/{key}/{path}` | Pobierz plik tekstowy (też CSV) |
| `download_bytes(path)` | `GET /data/{key}/{path}` | Pobierz plik binarny |
| `submit(task, answer)` | `POST /verify` | Wyślij odpowiedź; rzuca `RuntimeError` na błąd HTTP |
| `submit_raw(task, answer)` | `POST /verify` | Wyślij odpowiedź; zwraca surowy `Response` (bez rzucania wyjątku) |

#### Helpery (`src/utils/`)

| Funkcja | Plik | Opis |
|---------|------|------|
| `get_cached_or_download_text(file_name, hub)` | `download.py` | Cache w `cache/` |
| `load_person_locations_with_cache(hub, suspect)` | `download.py` | Cache lokalizacji per osoba |
| `geocode_city(city) -> (lat, lon)` | `download.py` | Nominatim OSM, szuka w Polsce |
| `save_task_artifact(task_name, answer, response)` | `artifacts.py` | Zapis do `outputs/ans_{task_name}.json` |
| `cache_text(task_name, content)` | `artifacts.py` | Zapis dowolnego JSON do `cache/{task_name}.json` |

---

## Docelowa ścieżka: skrypty → tools

```
src/scripts/task_XX.py          →  src/tools/tool_XX.py
monolityczny main()             →  małe Tool.run(input, state) → StepResult
wywoływany ręcznie z CLI        →  wywoływany przez LLM jako function call
```

Każda funkcja biznesowa (geocoding, distance calc, location lookup, package check) staje się osobnym `Tool`
z jasnym `dict` wejściem — LLM może je komponować przez `Plan(steps=[PlanStep(...), ...])`.

### Przykładowy tool do zaimplementowania

```python
# src/tools/geocode.py
class GeocodeTool(Tool):
    name = "geocode"
    help = "Zwraca współrzędne GPS dla podanego miasta w Polsce"

    def run(self, tool_input: dict[str, Any], state: AgentState) -> StepResult:
        city = tool_input.get("city", "")
        lat, lon = geocode_city(city)
        return StepResult(
            status=StepStatus.FINAL,
            output={"latitude": lat, "longitude": lon},
            message=f"{city}: {lat}, {lon}"
        )
```

---

## Katalogi robocze

| Katalog | Zawartość |
|---------|-----------|
| `cache/` | Pobrane pliki (nie pobieraj ponownie) |
| `cache/doc/` | Dokumenty z `hub.ag3nts.org/dane/doc` (task_04) |
| `cache/sensors/` | Pliki sensorów JSON (task_11, ~3100 plików) |
| `outputs/` | Artefakty zadań `ans_{task}.json` |
| `runs/` | Trace każdego uruchomienia agenta |
| `sessions/` | Historia sesji Flask proxy (per sessionID) |

---

## Zmienne środowiskowe (`.env.llm`)

| Zmienna | Opis |
|---------|------|
| `BIELIK_API_KEY` | Klucz NVIDIA API |
| `BIELIK_BASE_URL` | `https://integrate.api.nvidia.com/v1` |
| `BIELIK_MODEL` | `speakleash/bielik-11b-v2.6-instruct` |
| `AI_DEVS_API` | Klucz API kursu AI_Devs |
| `AI_DEVS_BASE_URL` | `https://hub.ag3nts.org` |
| `PACKAGES_API_URL` | `https://hub.ag3nts.org/api/packages` (task_03_proxy) |
