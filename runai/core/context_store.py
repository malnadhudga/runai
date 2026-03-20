import os
import json


class ContextStore:
    """Shared context that accumulates results from completed tasks."""

    def __init__(self, workspace_path: str = "workspace"):
        os.makedirs(os.path.join(workspace_path, "src"), exist_ok=True)
        os.makedirs(os.path.join(workspace_path, "logs"), exist_ok=True)
        self.store: dict[str, str] = {}
        self.context_file = os.path.join(workspace_path, "context.json")

    def set(self, task_id: str, result: str) -> None:
        self.store[task_id] = result
        with open(self.context_file, "w", encoding="utf-8") as f:
            json.dump(self.store, f, indent=2)

    def get(self, task_id: str) -> str | None:
        return self.store.get(task_id)

    def get_all(self) -> dict[str, str]:
        return dict(self.store)

    def summary(self) -> str:
        parts = []
        for task_id, result in self.store.items():
            parts.append(f"Task {task_id}:\n{result}")
        return "\n\n".join(parts)
