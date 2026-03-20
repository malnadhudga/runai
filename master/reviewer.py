from crew.core.llm_client import LLMClient
from crew.core.prompts import REVIEWER_SYSTEM_PROMPT


class Reviewer:
    """Reviews slave output and decides ACCEPT or RETRY."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def review(
        self,
        task_description: str,
        files: dict[str, str],
        summary: str,
        errors: str,
    ) -> tuple[str, str]:
        """Check a slave's output against the task requirements.

        Args:
            task_description: What the task asked for.
            files: Dict of {filename: contents} the slave produced.
            summary: The slave's own DONE: summary.
            errors: Any stderr output from running the code.

        Returns:
            (verdict, explanation) where verdict is ACCEPT or RETRY.
        """
        files_section = ""
        for name, content in files.items():
            files_section += f"\n--- {name} ---\n{content}\n"

        user_message = (
            f"TASK DESCRIPTION:\n{task_description}\n\n"
            f"FILES PRODUCED:{files_section}\n"
            f"AGENT SUMMARY:\n{summary}\n\n"
            f"ERROR OUTPUT:\n{errors or 'None'}\n"
        )

        response = self.llm_client.chat(
            [{"role": "user", "content": user_message}],
            system=REVIEWER_SYSTEM_PROMPT,
        )

        return self._parse_verdict(response)

    @staticmethod
    def _parse_verdict(response: str) -> tuple[str, str]:
        """Extract ACCEPT or RETRY from the first word of the response."""
        stripped = response.strip()
        first_line = stripped.split("\n", 1)[0].strip()

        if first_line.startswith("ACCEPT"):
            explanation = stripped[len("ACCEPT"):].strip().lstrip(":").strip()
            return ("ACCEPT", explanation or "Accepted.")
        if first_line.startswith("RETRY"):
            explanation = stripped[len("RETRY"):].strip().lstrip(":").strip()
            return ("RETRY", explanation or "Needs revision.")

        return ("RETRY", "Reviewer response unclear, please redo")
