from crew.core.task import Task


class SlaveAgent:
    """An autonomous coding agent that executes a single subtask."""

    def __init__(self, task: Task, context: str = ""):
        raise NotImplementedError

    def run(self) -> dict:
        raise NotImplementedError
