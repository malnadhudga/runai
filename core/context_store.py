class ContextStore:
    """Shared context that accumulates results from completed tasks."""

    def __init__(self):
        raise NotImplementedError

    def store(self, task_id: str, files: dict[str, str], summary: str) -> None:
        raise NotImplementedError

    def get_context_for(self, task_ids: list[str]) -> str:
        raise NotImplementedError

    def get_all_files(self) -> dict[str, str]:
        raise NotImplementedError
