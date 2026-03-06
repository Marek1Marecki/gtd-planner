"""Task repository interfaces and ports."""

# apps/tasks/ports/repositories.py
from abc import ABC, abstractmethod
from typing import Any

from apps.tasks.domain.entities import TaskEntity, TaskStatus


class ITaskRepository(ABC):
    """Interface for task repository operations."""

    @abstractmethod
    def get_by_id(self, task_id: int) -> TaskEntity | None:
        """Retrieve a task by its ID."""
        pass

    @abstractmethod
    def save(self, task: TaskEntity, user_id: int | None = None) -> TaskEntity:
        """Zapisuje (tworzy lub aktualizuje) zadanie i zwraca zaktualizowaną encję (np. z ID)."""
        pass

    @abstractmethod
    def filter_by_status(self, status: TaskStatus) -> list[TaskEntity]:
        """Filter tasks by their status."""
        pass

    @abstractmethod
    def get_active_tasks(self) -> list[TaskEntity]:
        """Get all active tasks (TODO or SCHEDULED)."""
        pass

    @abstractmethod
    def get_dependent_tasks(self, blocker_id: int) -> list[TaskEntity]:
        """Zwraca zadania, które są blokowane przez blocker_id."""
        pass

    @abstractmethod
    def has_active_blockers(self, task_id: int | None) -> bool:
        """Check if task has any active blockers."""
        pass

    @abstractmethod
    def increment_recurring_stats(self, pattern_id: int | None) -> None:
        """Zwiększa licznik completed_count w szablonie."""
        pass

    @abstractmethod
    def create(self, user_id: int, task_data: dict[str, Any]) -> TaskEntity:
        """Tworzy nowe zadanie."""
        pass

    @abstractmethod
    def update(self, task: TaskEntity, update_data: dict[str, Any]) -> TaskEntity:
        """Aktualizuje istniejące zadanie."""
        pass

    @abstractmethod
    def delete(self, task_id: int) -> None:
        """Usuwa zadanie."""
        pass

    @abstractmethod
    def get_by_user(self, user_id: int) -> list[TaskEntity]:
        """Zwraca wszystkie zadania użytkownika."""
        pass

    @abstractmethod
    def filter_by_user_and_status(self, user_id: int, status: TaskStatus) -> list[TaskEntity]:
        """Filtruje zadania użytkownika według statusu."""
        pass
