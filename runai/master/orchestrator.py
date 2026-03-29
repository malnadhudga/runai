import os
import time
import concurrent.futures

from runai.core.llm_client import LLMClient
from runai.core.task import Task
from runai.core.task_queue import TaskQueue
from runai.core.context_store import ContextStore
from runai.master.planner import Planner
from runai.master.reviewer import Reviewer
from runai.master.assembler import Assembler
from runai.master.dispatcher import Dispatcher
from runai.master.failure_handler import FailureHandler
from runai.tools.read_file import read_file
from runai.tools.run_code import run_code


MAX_RETRIES = 3
MAX_TOTAL_TASKS = 15
GLOBAL_TIMEOUT = 600  # 10 minutes


class Orchestrator:
    """Top-level loop: plan -> dispatch -> review -> assemble."""

    def __init__(self, llm_client: LLMClient, on_status_change=None):
        self.llm_client = llm_client
        self.on_status_change = on_status_change or (lambda task_id, status, **kw: None)
        self.context_store = ContextStore()
        self.planner = Planner(llm_client)
        self.reviewer = Reviewer(llm_client)
        self.assembler = Assembler(llm_client)
        self.dispatcher = Dispatcher(llm_client, self.context_store)
        self.failure_handler = FailureHandler(llm_client)
        self.all_tasks: list[Task] = []

    def run(self, user_goal: str, tasks=None) -> str:
        """Execute the full plan-dispatch-review-assemble pipeline.

        Args:
            user_goal: The user's coding goal in plain English.
            tasks: Optional pre-planned task list. Plans from scratch if None.

        Returns:
            The final handover summary string.
        """
        if tasks is None:
            tasks = self.planner.plan(user_goal)
        self.all_tasks = list(tasks)
        queue = TaskQueue(tasks)

        for t in tasks:
            self.on_status_change(t.task_id, "pending")

        start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            while queue.has_work():
                if time.time() - start > GLOBAL_TIMEOUT:
                    break

                futures: dict[concurrent.futures.Future, str] = {}
                while True:
                    task = queue.pop_ready()
                    if task is None:
                        break
                    self.on_status_change(task.task_id, "running")
                    future = executor.submit(self.dispatcher.dispatch, task)
                    futures[future] = task.task_id

                if not futures:
                    # No tasks could be dispatched and nothing is running →
                    # pending tasks are blocked by failed deps (deadlock). Stop.
                    if not queue.running:
                        break
                    time.sleep(0.5)
                    continue

                for future in concurrent.futures.as_completed(futures):
                    task_id = futures[future]
                    task_obj = self._find_task(task_id)

                    try:
                        result = future.result()
                    except Exception:
                        queue.mark_failed(task_id)
                        self.on_status_change(task_id, "failed")
                        continue

                    if result.get("stuck"):
                        self._handle_stuck(
                            queue, task_id, task_obj, result
                        )
                    else:
                        self._handle_normal(
                            queue, task_id, task_obj, result
                        )

                time.sleep(0.5)

        completed = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "result": t.result or "",
            }
            for t in queue.completed
            if t.status == "done"
        ]
        all_files = self._read_all_workspace_files()

        return self.assembler.assemble(user_goal, completed, all_files)

    def _handle_normal(self, queue: TaskQueue, task_id: str, task_obj: Task, result: dict) -> None:
        """Standard path: review and accept/retry/fail."""
        self.on_status_change(task_id, "reviewing")
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
            self.on_status_change(task_id, "done")
        elif task_obj.retries < MAX_RETRIES:
            queue.requeue(task_id, explanation)
            self.on_status_change(task_id, "pending")
        else:
            queue.mark_failed(task_id)
            self.on_status_change(task_id, "failed")

    def _handle_stuck(self, queue: TaskQueue, task_id: str, task_obj: Task, result: dict) -> None:
        """Smart recovery path: analyze failure and decide strategy."""
        analysis = self.failure_handler.analyze(
            result["failure_report"],
            self.context_store.summary(),
        )
        decision = analysis["decision"]

        if decision == "GUIDE":
            queue.requeue(task_id, analysis["payload"])
            self.on_status_change(task_id, "pending")

        elif decision == "SPLIT":
            new_task_dicts = analysis["payload"]
            if queue.total_task_count + len(new_task_dicts) > MAX_TOTAL_TASKS:
                queue.mark_failed(task_id)
                self.on_status_change(task_id, "failed")
                return
            new_tasks = []
            for item in new_task_dicts:
                new_tasks.append(Task(
                    task_id=item["id"],
                    description=item["description"],
                    depends_on=item.get("depends_on", []),
                ))
            queue.mark_superseded(task_id)
            task_obj.mark_superseded([t.task_id for t in new_tasks])
            queue.add_tasks(new_tasks)
            self.all_tasks.extend(new_tasks)
            self.on_status_change(task_id, "superseded")
            for t in new_tasks:
                self.on_status_change(
                    t.task_id, "pending",
                    description=t.description,
                    depends_on=t.depends_on,
                )

        elif decision == "REWRITE":
            new_id = f"{task_id}_v{task_obj.retries + 2}"
            new_task = Task(
                task_id=new_id,
                description=analysis["payload"],
                depends_on=list(task_obj.depends_on),
            )
            queue.mark_superseded(task_id)
            task_obj.mark_superseded([new_id])
            queue.add_tasks([new_task])
            self.all_tasks.append(new_task)
            self.on_status_change(task_id, "superseded")
            self.on_status_change(
                new_id, "pending",
                description=new_task.description,
                depends_on=new_task.depends_on,
            )

        else:  # ABORT
            queue.mark_failed(task_id)
            self.on_status_change(task_id, "failed")

    def _find_task(self, task_id: str) -> Task | None:
        for t in self.all_tasks:
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
