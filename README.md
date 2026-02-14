# AI_Devs 4 – Agent

This repository contains an experimental AI agent developed step by step during the AI_Devs 4 program.
The goal is to build a reusable, modular agent architecture instead of one-off scripts for individual tasks.

## Status

Day 1 completed:
- project structure
- Python virtual environment
- basic CLI entrypoint

Day 2 completed:
- session-based AgentState
- command dispatch via registry (no if/elif chain)
- persistent run trace
- each session generates a unique `run_id`
- trace saved to `runs/<run_id>.json`

## Requirements

- Python >= 3.12

## How to run

Create and activate virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
.venv\Scripts\activate     # Windows
```
## Run traces

Each program session generates a unique `run_id`.

After every user command, the full session trace is saved to:
`runs/<run_id>.json`

Trace format: 
```
[
  {
    "status": "FINAL",
    "message": "..."
  }
]
```
This enables:
- reproducibility
- debugging
- future replay / evaluation

## Architecture (current state)

- `cli/` – user interaction layer
- `agent/` – core execution logic
- `storage/` – persistence utilities
- `runs/` – generated session traces (ignored in git)