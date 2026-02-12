# Agent Execution Loop

## Purpose
Agent executes a task using an iterative decision loop.

## Input 
- User Task (text instructions)
- Optional initial context 
- Executional configuration (e.g. step limits)

## State
- History of executed steps
- Notes / Working memory
- Execution counters and limits

## Step
Each Step produces:
- status (FINAL | FAIL | CONTINUE | NEED_INPUT)
- optional message or data
- optional side effects

## Termination
Agents terminates when:
- FINAL is returned
- FAIL is returned
- Execution limits are exceeded
