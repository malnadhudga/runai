from crew.core.llm_client import LLMClient
from crew.core.prompts import ASSEMBLER_SYSTEM_PROMPT


class Assembler:
    """Produces the final handover summary from all completed tasks."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def assemble(
        self,
        user_goal: str,
        completed_tasks: list[dict],
        all_files: dict[str, str],
    ) -> str:
        """Build a handover document from all completed work.

        Args:
            user_goal: The original user request.
            completed_tasks: List of dicts with task_id, description, result.
            all_files: Dict of {filename: contents} in workspace/src/.

        Returns:
            A formatted summary string from the LLM.
        """
        tasks_section = ""
        for t in completed_tasks:
            tasks_section += f"- [{t['task_id']}] {t['description']}\n  Result: {t['result']}\n"

        files_section = ""
        for name, content in all_files.items():
            files_section += f"\n--- {name} ---\n{content}\n"

        user_message = (
            f"ORIGINAL GOAL:\n{user_goal}\n\n"
            f"COMPLETED TASKS:\n{tasks_section}\n"
            f"ALL FILES PRODUCED:{files_section}"
        )

        return self.llm_client.chat(
            [{"role": "user", "content": user_message}],
            system=ASSEMBLER_SYSTEM_PROMPT,
        )
