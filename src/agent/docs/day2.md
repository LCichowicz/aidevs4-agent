Day 2
## Goal

Build a minimal iterative agent structure:

- Agent – decision logic
- Runner – execution loop
- State – shared memory
- CLI – entry point

## What was implemented

### types.py

- StepStatus enum
- AgentInput
- StepResult
- AgentOutput

 Separated step-level result from full execution result.

### state.py

AgentState
- steps: list[StepResult]
- notes: dict[str, Any] using default_factory

Key point: mutable defaults require default_factory.

### agent.py

Implemented simple commands:
- help
- echo:
- countdown N

#### countdown:

- initializes counter in state.notes
- returns CONTINUE while counter > 1
- returns FINAL and clears state at the end

Agent updates state.notes.
Agent does not control the execution loop.

### runner.py

- creates AgentState
- loops up to max_steps
- appends StepResult to history
- stops when status != CONTINUE
- returns FAIL if limit exceeded

Runner controls execution flow only.
No domain logic inside runner.

## Main takeaways

- Clear separation between logic (Agent) and control flow (Runner).
- State must be passed as an instance, not accessed via class.
- Enum is safer than raw strings.
- Multi-step behavior requires persistent state.