"""
Task 12 — firmware

Goal: run /opt/firmware/cooler/cooler.bin on the remote VM, obtain the ECCS-... code
      and submit it to Centrala.

Approach (sequential agent):
1. Read .gitignore so we never touch forbidden files.
2. Find the binary password (stored in /home/operator/notes/pass.txt).
3. Fix settings.ini:
   - uncomment SAFETY_CHECK=pass
   - set test_mode.enabled=false
   - set cooling.enabled=true
4. Remove the cooler-is-blocked.lock file.
5. Run cooler.bin <password> and capture the ECCS-... code.
6. Submit to /verify.
"""

import re

from src.llm.shell_client import ShellClient
from src.llm.hub_client import HubClient
from src.utils.artifacts import save_task_artifact

TASK = "firmware"
FIRMWARE_DIR = "/opt/firmware/cooler"
BINARY = f"{FIRMWARE_DIR}/cooler.bin"
SETTINGS = f"{FIRMWARE_DIR}/settings.ini"
LOCK = f"{FIRMWARE_DIR}/cooler-is-blocked.lock"
GITIGNORE = f"{FIRMWARE_DIR}/.gitignore"
PASS_FILE = "/home/operator/notes/pass.txt"


def _data(result: dict) -> str:
    return result.get("data", "") or result.get("output", "")


def get_gitignore(shell: ShellClient) -> set[str]:
    result = shell.run_with_retry(f"cat {GITIGNORE}")
    lines = _data(result).splitlines()
    return {line.strip() for line in lines if line.strip()}


def find_password(shell: ShellClient) -> str:
    result = shell.run_with_retry(f"cat {PASS_FILE}")
    password = _data(result).strip()
    if not password:
        raise RuntimeError(f"Could not read password from {PASS_FILE}: {result}")
    return password


def read_settings(shell: ShellClient) -> list[str]:
    result = shell.run_with_retry(f"cat {SETTINGS}")
    return _data(result).splitlines()


def fix_settings(shell: ShellClient, lines: list[str]) -> None:
    """Patch settings.ini so the binary can start."""
    changes: dict[int, str] = {}

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Uncomment SAFETY_CHECK
        if stripped.startswith("#") and "SAFETY_CHECK" in stripped:
            changes[i] = stripped.lstrip("#").strip()
        # Disable test mode — find enabled=true under [test_mode]
        elif stripped == "enabled=true":
            for j in range(i - 2, -1, -1):
                if lines[j].strip().startswith("["):
                    if lines[j].strip() == "[test_mode]":
                        changes[i] = "enabled=false"
                    break
        # Enable cooling — find enabled=false under [cooling]
        elif stripped == "enabled=false":
            for j in range(i - 2, -1, -1):
                if lines[j].strip().startswith("["):
                    if lines[j].strip() == "[cooling]":
                        changes[i] = "enabled=true"
                    break

    if not changes:
        print("[settings] No changes needed.")
        return

    for line_no, new_content in sorted(changes.items()):
        old = lines[line_no - 1]
        print(f"  [settings] line {line_no}: {old!r} -> {new_content!r}")
        result = shell.run_with_retry(f"editline {SETTINGS} {line_no} {new_content}")
        if "error" in result:
            raise RuntimeError(f"editline failed on line {line_no}: {result}")


def remove_lock(shell: ShellClient) -> None:
    result = shell.run_with_retry(f"ls {FIRMWARE_DIR}")
    files = _data(result)
    if "cooler-is-blocked.lock" in files:
        print(f"[lock] Removing {LOCK}")
        result = shell.run_with_retry(f"rm {LOCK}")
        if "error" in result:
            raise RuntimeError(f"rm lock failed: {result}")
    else:
        print("[lock] No lock file present.")


def run_binary(shell: ShellClient, password: str) -> str:
    print(f"[binary] Running {BINARY} {password}")
    result = shell.run_with_retry(f"{BINARY} {password}")
    output = _data(result)
    print(f"[binary] Output:\n{output}")

    match = re.search(r"ECCS-[0-9a-f]+", output)
    if not match:
        raise RuntimeError(f"No ECCS code found in binary output: {result}")
    return match.group(0)


def main() -> None:
    shell = ShellClient()
    hub = HubClient()

    print("=== Task 12: firmware ===\n")

    # 1. Check gitignore
    ignored = get_gitignore(shell)
    print(f"[gitignore] Ignored: {ignored}")

    # 2. Find password
    password = find_password(shell)
    print(f"[password] Found: {password}")

    # 3. Fix settings.ini
    lines = read_settings(shell)
    print("[settings] Current:")
    for i, line in enumerate(lines, start=1):
        print(f"  {i}: {line}")
    fix_settings(shell, lines)

    # 4. Remove lock
    remove_lock(shell)

    # 5. Run binary and extract code
    code = run_binary(shell, password)
    print(f"\n[code] Confirmation code: {code}")

    # 6. Submit
    answer = {"confirmation": code}
    response = hub.submit_raw(TASK, answer)
    print(f"\n[hub] Response [{response.status_code}]: {response.text}")

    data = response.json() if response.ok else response.text
    save_task_artifact(TASK, answer, data)

    if response.ok and "FLG" in response.text:
        print("\n*** FLAG FOUND! ***")
        print(response.text)


if __name__ == "__main__":
    main()
