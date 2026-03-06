# apps/tasks/ports/repositories.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from apps.tasks.domain.entities import TaskEntity, TaskStatus


class ITaskRepository(ABC):
    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[TaskEntity]:
        pass

    @abstractmethod
    def save(self, task: TaskEntity, user_id: int | None = None) -> TaskEntity:
        """Zapisuje (tworzy lub aktualizuje) zadanie i zwraca zaktualizowaną encję (np. z ID)."""
        pass

    @abstractmethod
    def filter_by_status(self, status: TaskStatus) -> List[TaskEntity]:
        pass

    @abstractmethod
    def get_active_tasks(self) -> List[TaskEntity]:
        """Zwraca zadania todo i scheduled."""
        pass

    @abstractmethod
    def get_dependent_tasks(self, blocker_id: int) -> List[TaskEntity]:
        """Zwraca zadania, które są blokowane przez blocker_id."""
        pass

    @abstractmethod
    def has_active_blockers(self, task_id: int | None) -> bool:
        """Sprawdza, czy zadanie ma jakiekolwiek blokery w stanie niedokończonym."""
        pass

    @abstractmethod
    def increment_recurring_stats(self, pattern_id: int | None) -> None:
        """Zwiększa licznik completed_count w szablonie."""
        pass

    @abstractmethod
    def create(self, user_id: int, task_data: Dict[str, Any]) -> TaskEntity:
        """Tworzy nowe zadanie."""
        pass

    @abstractmethod
    def update(self, task: TaskEntity, update_data: Dict[str, Any]) -> TaskEntity:
        """Aktualizuje istniejące zadanie."""
        pass

    @abstractmethod
    def delete(self, task_id: int) -> None:
        """Usuwa zadanie."""
        pass

    @abstractmethod
    def get_by_user(self, user_id: int) -> List[TaskEntity]:
        """Zwraca wszystkie zadania użytkownika."""
        pass

    @abstractmethod
    def filter_by_user_and_status(self, user_id: int, status: TaskStatus) -> List[TaskEntity]:
        """Filtruje zadania użytkownika według statusu."""
        pass
