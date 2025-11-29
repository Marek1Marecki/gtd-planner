# apps/tasks/ports/repositories.py
from abc import ABC, abstractmethod
from typing import List, Optional
from apps.tasks.domain.entities import TaskEntity, TaskStatus


class ITaskRepository(ABC):
    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[TaskEntity]:
        pass

    @abstractmethod
    def save(self, task: TaskEntity) -> TaskEntity:
        """Zapisuje (tworzy lub aktualizuje) zadanie i zwraca zaktualizowaną encję (np. z ID)."""
        pass

    @abstractmethod
    def filter_by_status(self, status: TaskStatus) -> List[TaskEntity]:
        pass

    @abstractmethod
    def get_active_tasks(self) -> List[TaskEntity]:
        """Zwraca zadania todo i scheduled."""
        pass