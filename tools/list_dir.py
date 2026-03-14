import os

WORKSPACE_SRC = os.path.join("workspace", "src")


def list_dir(path: str = "") -> str:
    """List files in the given directory inside workspace/src/."""
    full_path = os.path.join(WORKSPACE_SRC, path)
    if not os.path.isdir(full_path):
        return "empty"
    entries = os.listdir(full_path)
    if not entries:
        return "empty"
    return "\n".join(sorted(entries))
