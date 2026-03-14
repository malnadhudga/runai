from crew.core.llm_client import LLMClient


class Reviewer:
    """Reviews slave output and decides ACCEPT or RETRY."""

    def __init__(self, llm_client: LLMClient):
        raise NotImplementedError

    def review(self, task_description: str, files: dict[str, str], summary: str, errors: str) -> tuple[str, str]:
        raise NotImplementedError
