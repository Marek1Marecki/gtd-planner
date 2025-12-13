# apps/tasks/domain/entities.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    INBOX = 'inbox'
    TODO = 'todo'
    SCHEDULED = 'scheduled'
    DONE = 'done'
    WAITING = 'waiting'
    BLOCKED = 'blocked'
    DELEGATED = 'delegated'
    POSTPONED = 'postponed'
    PAUSED = 'paused'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'


@dataclass
class TaskEntity:
    id: Optional[int]  # ID może być None przed zapisem
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.INBOX

    # Czas
    duration_min: Optional[int] = None  # minuty
    duration_max: Optional[int] = None  # minuty
    due_date: Optional[datetime] = None
    is_fixed_time: bool = False

    # Priorytety
    priority: int = 3  # 1-5
    energy_required: int = 2  # 1-3
    complexity: int = 1  # 1-5

    # Kontekst
    is_private: bool = False
    percent_complete: int = 0  # dla Paused

    is_critical_path: bool = False  # Flaga CPM

    # Relacje (tylko ID, żeby nie wiązać obiektów domenowych z ORM)
    project_id: Optional[int] = None
    goal_id: Optional[int] = None
    context_id: Optional[int] = None
    area_id: Optional[int] = None
    area_color: Optional[str] = None
    goal_deadline: Optional[datetime] = None
    project_deadline: Optional[datetime] = None


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
        return self.status in [TaskStatus.TODO, TaskStatus.SCHEDULED]