import json
import re

from runai.core.llm_client import LLMClient
from runai.core.task import Task
from runai.core.prompts import PLANNER_SYSTEM_PROMPT


class Planner:
    """Breaks a user goal into atomic subtasks using the LLM."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences if the model wraps its JSON in them."""
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()

    def plan(self, goal: str) -> list[Task]:
        messages = [{"role": "user", "content": goal}]
        raw = self.llm_client.chat(messages, system=PLANNER_SYSTEM_PROMPT)

        try:
            items = json.loads(self._strip_fences(raw))
        except json.JSONDecodeError:
            retry_msg = (
                "Your previous response was not valid JSON. "
                "Return ONLY the JSON array, no other text."
            )
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": retry_msg})
            raw = self.llm_client.chat(messages, system=PLANNER_SYSTEM_PROMPT)
            try:
                items = json.loads(self._strip_fences(raw))
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Planner failed to return valid JSON after retry: {raw!r}"
                ) from e

        tasks = []
        for item in items:
            tasks.append(Task(
                task_id=item["id"],
                description=item["description"],
                depends_on=item.get("depends_on", []),
            ))
        return tasks
