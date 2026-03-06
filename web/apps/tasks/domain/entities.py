"""Task domain entities."""

# apps/tasks/domain/entities.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TaskStatus(StrEnum):
    """Enumeration of possible task statuses."""

    INBOX = "inbox"
    TODO = "todo"
    SCHEDULED = "scheduled"
    DONE = "done"
    WAITING = "waiting"
    BLOCKED = "blocked"
    DELEGATED = "delegated"
    POSTPONED = "postponed"
    PAUSED = "paused"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


@dataclass
class TaskEntity:
    """Represents a task in the domain layer."""

    id: int | None  # ID może być None przed zapisem
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.INBOX
    user_id: int | None = None  # User ownership

    # Czas
    duration_min: int | None = None  # minuty
    duration_max: int | None = None  # minuty
    due_date: datetime | None = None
    is_fixed_time: bool = False

    # Priorytety
    priority: int = 3  # 1-5
    energy_required: int = 2  # 1-3
    complexity: int = 1  # 1-5

    # Kontekst
    is_private: bool = False
    percent_complete: int = 0  # dla Paused

    is_critical_path: bool = False  # Flaga CPM
    is_milestone: bool = False

    # Relacje (tylko ID, żeby nie wiązać obiektów domenowych z ORM)
    project_id: int | None = None
    goal_id: int | None = None
    context_id: int | None = None
    area_id: int | None = None
    area_color: str | None = None
    goal_deadline: datetime | None = None
    project_deadline: datetime | None = None
    ready_since: datetime | None = None
    recurring_pattern_id: int | None = None
    blocked_by: list[int] = field(default_factory=list)

    created_at: datetime | None = None

    @property
    def duration_expected(self) -> int:
        """Oblicza d_exp (średnia)."""
        if self.duration_min and self.duration_max:
            avg = (self.duration_min + self.duration_max) / 2
            return int(avg)
        return self.duration_min or 30  # default

    @property
    def effective_duration(self) -> int:
        """Czas pozostały do wykonania (dla Paused)."""
        base = self.duration_expected
        if self.status == TaskStatus.PAUSED and self.percent_complete > 0:
            remaining = base * (1 - self.percent_complete / 100)
            return max(1, int(remaining))
        return base

    def is_active(self) -> bool:
        """Check if task is in active status."""
        return self.status in [TaskStatus.TODO, TaskStatus.SCHEDULED]
