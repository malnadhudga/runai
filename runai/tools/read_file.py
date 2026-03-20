import os

WORKSPACE_SRC = os.path.join("workspace", "src")


def read_file(filepath: str) -> str:
    """Read and return the contents of a file inside workspace/src/."""
    full_path = os.path.join(WORKSPACE_SRC, filepath)
    if not os.path.isfile(full_path):
        return f"error: file not found — {filepath}"
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()
