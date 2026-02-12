Day 1
## Goal

Set up basic project structure for an experimental agent.

### Project setup

- Python 3.12+
- virtual environment
- module-based structure (src/...)
- CLI entrypoint

### Structure created

- src/agent/
- src/cli/
- basic main.py
- initial README
- .gitignore updates

### Key decisions

- Run project as module:

python -m src.cli.main

- Keep agent logic separate from CLI.
- Avoid writing a single monolithic script.

## Notes

- This project will focus on architecture first, features later.
- Start simple, iterate.