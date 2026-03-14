from crew.core.task import Task
from crew.core.context_store import ContextStore


class Dispatcher:
    """Assigns ready tasks to slave agents and collects results."""

    def __init__(self, context_store: ContextStore):
        raise NotImplementedError

    def dispatch(self, task: Task) -> dict:
        raise NotImplementedError
