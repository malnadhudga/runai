from crew.core.llm_client import LLMClient
from crew.core.task import Task
from crew.slave.scratchpad import Scratchpad
from crew.slave.react_loop import ReActLoop
from crew.tools import TOOLS


class SlaveAgent:
    """An autonomous coding agent that executes a single subtask."""

    def __init__(self, task: Task, context: str, llm_client: LLMClient):
        self.task = task
        self.scratchpad = Scratchpad(slave_id=task.task_id, task=task)
        self.react_loop = ReActLoop(llm_client, self.scratchpad, TOOLS)

        initial_message = ""
        if context:
            initial_message += f"Context from prior tasks:\n{context}\n\n"
        initial_message += f"Task: {task.description}"
        if task.review_notes:
            initial_message += f"\n\nReviewer feedback from previous attempt:\n{task.review_notes}"

        self.scratchpad.append_user(initial_message)

    def run(self) -> dict:
        """Run the ReAct loop until done or max iterations, then return results."""
        while not self.react_loop.is_done():
            self.react_loop.step()

        return {
            "task_id": self.task.task_id,
            "result": self.react_loop.result or "max iterations reached",
            "output_files": self.scratchpad.files_written,
            "stuck": self.react_loop.stuck,
            "failure_report": self.react_loop.failure_report,
        }
