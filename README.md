# AI_Devs 4 -- Agent

This repository contains an experimental AI agent developed step by step
during the AI_Devs 4 program.

The goal is to build a reusable, modular agent architecture instead of
one-off scripts for individual tasks.

The project evolves incrementally, with each "Day" introducing a new
architectural component.

------------------------------------------------------------------------

# Status

### Day 1 -- Project Setup

-   project structure
-   Python virtual environment
-   basic CLI entrypoint

### Day 2 -- Core Agent Skeleton

-   AgentState implementation
-   StepResult and AgentOutput models
-   basic agent logic (echo, help, countdown)
-   separation of agent logic and execution loop

### Day 3 -- Planning Models

Introduced stable planning models:

-   `PlanStep`
-   `Plan`
-   `AgentContext`

These models define the structure used by the planning layer.

#### Frozen Interface Rule

From this point, the structure of `Plan` and `PlanStep` is considered
stable.

Any future changes must remain backward-compatible.

### Day 4 -- Execution Engine and Run Trace

Implemented the full execution loop and structured trace system:

-   runner execution loop with `max_steps` guard
-   step-by-step execution using `StepStatus`
-   support for multi-step tools
-   structured execution trace
-   JSON-safe serialization
-   persistent run traces stored in `runs/`

Each user command now produces an independent execution run.

### Day 5 -- Document Understanding and OCR (task_04_sendit)

Implemented document ingestion pipeline for railway shipment declarations:

-   `task_04_sendit.py` -- loads documentation from `hub.ag3nts.org/dane/doc`
-   recursive document loader following `include file=` directives in Markdown
-   file-type routing: `.md`/`.txt` loaded as text, images passed to Tesseract OCR
-   `pytesseract` + `Pillow` for OCR (polish language, grayscale preprocessing)
-   template extraction from loaded docs (header/marker-based search)
-   declaration rendered by Bielik LLM from extracted template + shipment data
-   post-render validation: required fields check + empty special-notes check
-   answer submitted to course hub via `hub.submit("sendit", {...})`
-   documents cached in `cache/doc/`
-   new dependencies: `pytesseract>=0.3.10`, `Pillow>=10.0.0`

### Day 7 -- Circuit Board Tile Rotation Puzzle (task_07_electricity)

Solved a 3×3 tile-rotation puzzle ("electricity circuit board"):

-   `task_07_electricity.py` -- submits tile rotation commands to the course hub
-   board is reset before each run via a dedicated `?reset=1` query parameter
-   `ROTATION_PLAN` encodes how many 90° clockwise rotations each grid cell (`RxC`) needs
-   `execute_rotation_plan` iterates the plan and calls `hub.submit("electricity", {"rotate": "RxC"})` for every non-zero entry
-   current and solved reference images downloaded and cached in `cache/` (`electricity.png`, `solved_electricity.png`)
-   local `get_cached_bytes` helper avoids re-downloading on repeated runs

### Day 8 -- Log Analysis and LLM Compression (task_08_failure)

Analyzed a nuclear power plant failure log:

-   `task_08_failure.py` -- downloads `failure.log`, filters `CRIT` events, compresses messages with LLM, submits cleaned log
-   `parse_log_line` -- regex parser for `[timestamp] [LEVEL] message` format
-   `msg_extract` -- Bielik LLM rewrites each CRIT message into a single compact line (preserving component names and original meaning)
-   `render_log` -- deduplicates by message and renders the final log string
-   intermediate results cached to `cache/failure_crit.json` and `cache/log_clean.json`
-   answer submitted via `hub.submit("failure", {"logs": log})`
-   `cache_text(task_name, content)` added to `src/utils/artifacts.py` for JSON caching to `cache/`

### Day 6 -- API Sequencing and LLM Categorization (task_05, task_06)

Two new task scripts:

**task_05_railway.py** -- Railway route reconfiguration via multi-step API:

-   opens route `X-01` by executing `reconfigure → setstatus(RTOPEN) → save` in sequence
-   `submit_with_retry` handles 429/503 rate-limiting: reads `retry_after` from body or
    `Retry-After` header, falls back to exponential backoff (capped at 30 s)
-   uses `hub.submit_raw()` to inspect raw HTTP response without raising on error status
-   `HubClient` extended with `submit_raw` / `post_json_raw` for raw-response access

**task_06_categorize.py** -- Per-item LLM classification from CSV:

-   downloads `categorize.csv` via `hub.download_text()`
-   classifies each item as `DNG` (dangerous) or `NEU` (neutral) using a prompt template
-   custom `reorder_items` reorders the item list to match expected submission order
-   resets the hub session with `{"prompt": "reset"}` before each attempt
-   submits one prompt per item; stops on flag (`FLG:`) or first error

------------------------------------------------------------------------

# Requirements

-   Python \>= 3.12

------------------------------------------------------------------------

## How to run

Create and activate virtual environment:

``` bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
.venv\Scripts\activate     # Windows
```

Run the CLI agent:

``` bash
python -m src.cli.main
```

------------------------------------------------------------------------

## Run traces

Each user command produces a **separate execution run**.

Trace files are stored in:

    runs/<run_id>.json

Example structure:

``` json
{
  "run_id": "20260307_203915",
  "trace_version": 1,
  "steps": [
    {
      "step_index": 0,
      "status": "CONTINUE",
      "tool": "countdown",
      "tool_input": {"n": "5"},
      "output": {"current": 5},
      "error": null,
      "message": "5"
    }
  ],
  "summary": {
    "steps_count": 6,
    "final_status": "FINAL"
  }
}
```

Trace files enable:

-   debugging
-   reproducibility
-   evaluation
-   future replay

------------------------------------------------------------------------

## Architecture (current state)

    src/
     ├─ cli/        – user interaction layer
     ├─ agent/      – agent runtime and execution logic
     ├─ tools/      – tool implementations and registry
     ├─ storage/    – persistence and serialization
     ├─ llm/        – LLMClient (Bielik), HubClient (course API)
     ├─ utils/      – cache/download helpers, geocoding, artifacts
     └─ scripts/    – standalone course task scripts

    cache/doc/      – cached documentation files (text + images)
    runs/           – generated execution traces
    sessions/       – Flask proxy session histories
    outputs/        – task answer artifacts (ans_*.json)

Core concepts:

-   **Agent** -- interprets tasks and selects tools
-   **Runner** -- controls execution loop
-   **AgentState** -- shared runtime state
-   **StepResult** -- result of a single step
-   **Run Trace** -- persistent record of agent execution

## Current status

8 out of 25 tasks complete (+ secret task).

The project contains:
- standalone task scripts (`task_01` through `task_08`)
- helper modules shared across tasks (`src/llm/`, `src/utils/`)
- Flask proxy workflow for task 03
- agent framework (`src/agent/`, `src/tools/`) ready for tool-driven execution

The structure is still evolving as more course tasks are implemented.