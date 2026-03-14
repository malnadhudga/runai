from crew.core.task import Task


class TaskQueue:
    """Manages ordering and dispatch of tasks respecting dependencies."""

    def __init__(self):
        raise NotImplementedError

    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_ready_tasks(self) -> list[Task]:
        raise NotImplementedError

    def mark_done(self, task_id: str) -> None:
        raise NotImplementedError

    def all_done(self) -> bool:
        raise NotImplementedError
