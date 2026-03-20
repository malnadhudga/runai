from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runai.core.task import Task


class Scratchpad:
    """Accumulates the thought/action/observation trace for a slave agent."""

    def __init__(self, slave_id: str, task: Task | None, max_iterations: int = 15):
        self.slave_id = slave_id
        self.task = task
        self.max_iterations = max_iterations
        self.messages: list[dict] = []
        self.files_written: list[str] = []
        self.iteration: int = 0

    def append_system(self, content: str) -> None:
        self.messages.append({"role": "system", "content": content})

    def append_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def append_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def append_tool_result(self, tool_name: str, result: str) -> None:
        self.messages.append({
            "role": "user",
            "content": f"Tool result ({tool_name}):\n{result}",
        })

    def is_maxed_out(self) -> bool:
        return self.iteration >= self.max_iterations

    def increment(self) -> None:
        self.iteration += 1

    def get_messages(self) -> list[dict]:
        return [m for m in self.messages if m["role"] != "system"]
