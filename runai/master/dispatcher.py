from runai.core.llm_client import LLMClient
from runai.core.task import Task
from runai.core.context_store import ContextStore
from runai.slave.agent import SlaveAgent


class Dispatcher:
    """Assigns ready tasks to slave agents and collects results."""

    def __init__(self, llm_client: LLMClient, context_store: ContextStore):
        self.llm_client = llm_client
        self.context_store = context_store

    def dispatch(self, task: Task) -> dict:
        """Run a single task through a SlaveAgent and return the result.

        Args:
            task: The Task to execute.

        Returns:
            Dict with task_id, result, and output_files.
        """
        context = self.context_store.summary()
        agent = SlaveAgent(task=task, context=context, llm_client=self.llm_client)
        return agent.run()
