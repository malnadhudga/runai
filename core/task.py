class Task:
    """Represents a single atomic subtask in the crew system."""

    def __init__(self, task_id: str, description: str, depends_on: list[str] | None = None):
        raise NotImplementedError

    def mark_complete(self, result: str) -> None:
        raise NotImplementedError

    def mark_failed(self, error: str) -> None:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError
