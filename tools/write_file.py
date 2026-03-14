import os

WORKSPACE_SRC = os.path.join("workspace", "src")


def write_file(filepath: str, content: str) -> str:
    """Write content to a file inside workspace/src/."""
    full_path = os.path.join(WORKSPACE_SRC, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        n = f.write(content)
    return f"ok: wrote {n} bytes to {filepath}"
