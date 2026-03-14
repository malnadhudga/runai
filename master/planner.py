from crew.core.llm_client import LLMClient
from crew.core.task import Task


class Planner:
    """Breaks a user goal into atomic subtasks using the LLM."""

    def __init__(self, llm_client: LLMClient):
        raise NotImplementedError

    def plan(self, user_goal: str) -> list[Task]:
        raise NotImplementedError
