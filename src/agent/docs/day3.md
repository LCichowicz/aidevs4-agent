# Day 3

## Goal

Introduce stable planning models that will later allow the agent to
separate **planning** from **execution**.

The goal was not to implement planning yet, but to define a clear and
future-proof structure for plans.

------------------------------------------------------------------------

## What was implemented

### PlanStep

Represents a single step in a plan.

Fields:

-   `tool` -- tool name
-   `input` -- dictionary containing tool arguments

Conceptual structure:

    PlanStep:
      tool: str
      input: dict

This model describes **what tool should be executed and with which
input**.

------------------------------------------------------------------------

### Plan

Represents a sequence of planned steps.

Structure:

    Plan:
      steps: list[PlanStep]

A plan is essentially an ordered list of actions the agent should
perform.

------------------------------------------------------------------------

### AgentContext

Introduced as a container for contextual information required by
planning and execution.

This allows future extensions such as:

-   conversation history
-   environment state
-   retrieved documents
-   memory

------------------------------------------------------------------------

## Frozen Interface Rule

From this point forward:

-   `PlanStep`
-   `Plan`

are considered **stable interfaces**.

This means:

-   new fields must be backward-compatible
-   structural changes should be avoided

The goal is to ensure that the planning layer can evolve without
breaking execution components.

------------------------------------------------------------------------

## Main takeaways

-   Planning and execution should be **separate concerns**.
-   Defining stable data models early prevents large refactors later.
-   Plans should describe **what to do**, not **how to execute it**.
-   Execution logic should remain inside the runner/agent layer.
