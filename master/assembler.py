from crew.core.llm_client import LLMClient


class Assembler:
    """Produces the final handover summary from all completed tasks."""

    def __init__(self, llm_client: LLMClient):
        raise NotImplementedError

    def assemble(self, user_goal: str, completed_tasks: list[dict], all_files: dict[str, str]) -> str:
        raise NotImplementedError
