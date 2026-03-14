from collections import deque

from crew.core.task import Task


class TaskQueue:
    """Manages ordering and dispatch of tasks respecting dependencies."""

    def __init__(self, tasks: list[Task]):
        self.pending: deque[Task] = deque(tasks)
        self.running: dict[str, Task] = {}
        self.completed: list[Task] = []
        self.failed: list[Task] = []

    def pop_ready(self) -> Task | None:
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

    def requeue(self, task_id: str, review_notes: str) -> None:
        task = self.running.pop(task_id)
        task.review_notes = review_notes
        task.retries += 1
        task.status = "pending"
        self.pending.append(task)

    def is_complete(self) -> bool:
        return len(self.pending) == 0 and len(self.running) == 0

    def has_work(self) -> bool:
        return len(self.pending) > 0 or len(self.running) > 0

    def all_task_ids_done(self) -> set[str]:
        return {t.task_id for t in self.completed}
