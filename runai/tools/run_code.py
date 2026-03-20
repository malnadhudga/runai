import os
import subprocess
import sys

WORKSPACE_SRC = os.path.join("workspace", "src")
TIMEOUT_SECONDS = 15
MAX_OUTPUT_CHARS = 2000


def run_code(filepath: str) -> str:
    """Execute a Python file and return stdout + stderr."""
    full_path = os.path.join(WORKSPACE_SRC, filepath)
    if not os.path.isfile(full_path):
        return f"error: file not found — {filepath}"
    try:
        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=WORKSPACE_SRC,
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"error: timed out after {TIMEOUT_SECONDS}s"
    except Exception as e:
        return f"error: {e}"
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n... (truncated)"
    return output
