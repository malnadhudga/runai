import os
import time
import concurrent.futures

from crew.core.llm_client import LLMClient
from crew.core.task_queue import TaskQueue
from crew.core.context_store import ContextStore
from crew.master.planner import Planner
from crew.master.reviewer import Reviewer
from crew.master.assembler import Assembler
from crew.master.dispatcher import Dispatcher
from crew.tools.read_file import read_file
from crew.tools.run_code import run_code


MAX_RETRIES = 3
GLOBAL_TIMEOUT = 600  # 10 minutes


class Orchestrator:
    """Top-level loop: plan -> dispatch -> review -> assemble."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.context_store = ContextStore()
        self.planner = Planner(llm_client)
        self.reviewer = Reviewer(llm_client)
        self.assembler = Assembler(llm_client)
        self.dispatcher = Dispatcher(llm_client, self.context_store)

    def run(self, user_goal: str) -> str:
        """Execute the full plan-dispatch-review-assemble pipeline.

        Args:
            user_goal: The user's coding goal in plain English.

        Returns:
            The final handover summary string.
        """
        tasks = self.planner.plan(user_goal)
        queue = TaskQueue(tasks)

        print("=== TASK PLAN ===")
        for t in tasks:
            print(f"  {t.task_id}: {t.description}")
        print()

        start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            while queue.has_work():
                if time.time() - start > GLOBAL_TIMEOUT:
                    print("Global timeout reached, stopping.")
                    break

                futures: dict[concurrent.futures.Future, str] = {}
                while True:
                    task = queue.pop_ready()
                    if task is None:
                        break
                    print(f"  >> dispatching {task.task_id}")
                    future = executor.submit(self.dispatcher.dispatch, task)
                    futures[future] = task.task_id

                if not futures:
                    time.sleep(0.5)
                    continue

                for future in concurrent.futures.as_completed(futures):
                    task_id = futures[future]
                    task_obj = self._find_task(tasks, task_id)

                    try:
                        result = future.result()
                    except Exception as e:
                        print(f"  {task_id} CRASHED: {e}")
                        queue.mark_failed(task_id)
                        continue

                    files = self._read_output_files(result.get("output_files", []))
                    errors = self._run_output_files(result.get("output_files", []))

                    verdict, explanation = self.reviewer.review(
                        task_description=task_obj.description,
                        files=files,
                        summary=result.get("result", ""),
                        errors=errors,
                    )

                    if verdict == "ACCEPT":
                        queue.mark_done(
                            task_id,
                            result.get("result", ""),
                            result.get("output_files", []),
                        )
                        self.context_store.set(task_id, result.get("result", ""))
                        print(f"  {task_id} ACCEPTED")
                    elif task_obj.retries < MAX_RETRIES:
                        queue.requeue(task_id, explanation)
                        print(f"  {task_id} RETRY (attempt {task_obj.retries})")
                    else:
                        queue.mark_failed(task_id)
                        print(f"  {task_id} FAILED after {MAX_RETRIES} retries")

                time.sleep(0.5)

        completed = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "result": t.result or "",
            }
            for t in queue.completed
        ]
        all_files = self._read_all_workspace_files()

        return self.assembler.assemble(user_goal, completed, all_files)

    @staticmethod
    def _find_task(tasks: list, task_id: str):
        for t in tasks:
            if t.task_id == task_id:
                return t
        return None

    @staticmethod
    def _read_output_files(filenames: list[str]) -> dict[str, str]:
        result = {}
        for name in filenames:
            content = read_file(name)
            if not content.startswith("error:"):
                result[name] = content
        return result

    @staticmethod
    def _run_output_files(filenames: list[str]) -> str:
        errors = []
        for name in filenames:
            if name.endswith(".py"):
                output = run_code(name)
                if output.strip():
                    errors.append(f"--- {name} ---\n{output}")
        return "\n".join(errors) if errors else ""

    @staticmethod
    def _read_all_workspace_files() -> dict[str, str]:
        src_dir = os.path.join("workspace", "src")
        result = {}
        if not os.path.isdir(src_dir):
            return result
        for name in os.listdir(src_dir):
            filepath = os.path.join(src_dir, name)
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    result[name] = f.read()
        return result
