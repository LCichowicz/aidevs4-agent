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

#### task_04_sendit.py — Document ingestion + OCR + deklaracja kolejowa

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

#### LLMClient (`src/llm/client.py`) — Bielik 11B via NVIDIA API

| Metoda | Opis |
|--------|------|
| `chat(messages) -> str` | Zwykłe zapytanie, temperatura=0 |
| `chat_json_schema(messages, schema) -> Any` | Odpowiedź zgodna ze schematem JSON |

#### HubClient (`src/llm/hub_client.py`) — API kursu AI_Devs

| Metoda | Endpoint | Opis |
|--------|----------|------|
| `get_person_locations(name, surname)` | `POST /api/location` | Lokalizacje osoby |
| `get_access_level(name, surname, birth_year)` | `POST /api/accesslevel` | Poziom dostępu |
| `download_text(path)` | `GET /data/{key}/{path}` | Pobierz plik tekstowy |
| `download_bytes(path)` | `GET /data/{key}/{path}` | Pobierz plik binarny |
| `submit(task, answer)` | `POST /verify` | Wyślij odpowiedź do kursu |

#### Helpery (`src/utils/`)

| Funkcja | Plik | Opis |
|---------|------|------|
| `get_cached_or_download_text(file_name, hub)` | `download.py` | Cache w `cache/` |
| `load_person_locations_with_cache(hub, suspect)` | `download.py` | Cache lokalizacji per osoba |
| `geocode_city(city) -> (lat, lon)` | `download.py` | Nominatim OSM, szuka w Polsce |
| `save_task_artifact(task_name, answer, response)` | `artifacts.py` | Zapis do `outputs/ans_{task_name}.json` |

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
