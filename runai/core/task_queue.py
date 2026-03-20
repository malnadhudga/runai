from runai.core.task import Task


class TaskQueue:
    """Manages ordering and dispatch of tasks respecting dependencies.

    Uses priority scoring so higher-value tasks (fewer deps, more
    dependents, recovery tasks) run first.
    """

    def __init__(self, tasks: list[Task]):
        self.pending: list[Task] = list(tasks)
        self.running: dict[str, Task] = {}
        self.completed: list[Task] = []
        self.failed: list[Task] = []
        self.all_tasks: list[Task] = list(tasks)
        self._sort_pending()

    def _calculate_priority(self, task: Task) -> int:
        """Lower number = higher priority."""
        score = len(task.depends_on) * 10
        dependents = sum(
            1 for t in self.all_tasks if task.task_id in t.depends_on
        )
        score -= dependents * 5
        score += task.retries * 3
        # recovery tasks from SPLIT get a priority boost
        if "_s" in task.task_id:
            score -= 15
        return score

    def _sort_pending(self) -> None:
        self.pending.sort(key=self._calculate_priority)

    def pop_ready(self) -> Task | None:
        """Pop the highest-priority task whose deps are all done."""
        done_ids = self.all_task_ids_done()
        for i, task in enumerate(self.pending):
            if set(task.depends_on).issubset(done_ids):
                del self.pending[i]
                task.status = "running"
                self.running[task.task_id] = task
                return task
        return None

    def mark_done(self, task_id: str, result: str, output_files: list[str]) -> None:
        task = self.running.pop(task_id)
        task.result = result
        task.output_files = output_files
        task.status = "done"
        self.completed.append(task)

    def mark_failed(self, task_id: str) -> None:
        task = self.running.pop(task_id)
        task.status = "failed"
        self.failed.append(task)

    def mark_superseded(self, task_id: str) -> None:
        """Move a running task to completed as superseded (replaced by sub-tasks)."""
        task = self.running.pop(task_id)
        task.status = "superseded"
        self.completed.append(task)

    def requeue(self, task_id: str, review_notes: str) -> None:
        task = self.running.pop(task_id)
        task.review_notes = review_notes
        task.retries += 1
        task.status = "pending"
        self.pending.append(task)
        self._sort_pending()

    def add_tasks(self, new_tasks: list[Task]) -> None:
        """Inject new tasks mid-run (from SPLIT or REWRITE)."""
        for task in new_tasks:
            self.pending.append(task)
            self.all_tasks.append(task)
        self._sort_pending()

    def is_complete(self) -> bool:
        return len(self.pending) == 0 and len(self.running) == 0

    def has_work(self) -> bool:
        return len(self.pending) > 0 or len(self.running) > 0

    def all_task_ids_done(self) -> set[str]:
        return {t.task_id for t in self.completed}

    @property
    def total_task_count(self) -> int:
        return len(self.all_tasks)
