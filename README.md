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

    runs/           – generated execution traces

Core concepts:

-   **Agent** -- interprets tasks and selects tools
-   **Runner** -- controls execution loop
-   **AgentState** -- shared runtime state
-   **StepResult** -- result of a single step
-   **Run Trace** -- persistent record of agent execution

## Current status

The repository now includes the first AI_Devs course task solutions and early experiments toward a tool-driven agent architecture.

At this stage the project contains:
- standalone task scripts,
- helper modules shared across tasks,
- an early proxy workflow for task 03,
- ongoing agent-related refactoring and experiments.

The structure is still evolving and may change as more course tasks are implemented.