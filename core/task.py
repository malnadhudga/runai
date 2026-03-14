from dataclasses import dataclass, field


@dataclass
class Task:
    """Represents a single atomic subtask in the crew system."""

    task_id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    assigned_to: str | None = None
    output_files: list[str] = field(default_factory=list)
    result: str | None = None
    review_notes: str | None = None
    retries: int = 0

    def mark_complete(self, result: str) -> None:
        self.status = "done"
        self.result = result

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.result = error

    def to_dict(self) -> dict:
        return {
            "id": self.task_id,
            "description": self.description,
            "depends_on": self.depends_on,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "output_files": self.output_files,
            "result": self.result,
            "review_notes": self.review_notes,
            "retries": self.retries,
        }
