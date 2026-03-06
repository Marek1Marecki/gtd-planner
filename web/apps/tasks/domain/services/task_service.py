"""Task domain services for task management."""

# apps/tasks/domain/services/task_service.py
from typing import Any

from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository


class TaskService:
    """Service for task management operations."""

    def __init__(self, repository: ITaskRepository):
        """Initialize task service with repository."""
        self.repository = repository

    def complete_task(self, task_id: int) -> TaskEntity:
        """Oznacza zadanie jako wykonane i uruchamia odblokowywanie."""
        # 1. Pobierz zadanie
        task = self.repository.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        # 2. Zmień status na DONE
        update_data = {"status": TaskStatus.DONE}
        return self.repository.update(task, update_data)

    def _process_dependencies(self, completed_task_id: int) -> None:
        """Znajdź zadania zablokowane przez to zadanie i spróbuj je odblokować."""
        # Pobieramy ID zadań, które były blokowane przez completed_task_id
        # (Wymaga nowej metody w repozytorium: get_dependent_tasks)
        dependent_tasks = self.repository.get_dependent_tasks(completed_task_id)

        for dep_task in dependent_tasks:
            # Sprawdź, czy ma jeszcze INNE aktywne blokady
            # (Wymaga metody: has_active_blockers)
            if not self.repository.has_active_blockers(dep_task.id):
                # Jeśli nie ma innych blokerów -> Odblokuj!
                if dep_task.status == TaskStatus.BLOCKED:
                    dep_task.status = TaskStatus.TODO
                    self.repository.save(dep_task, user_id=None)
                    print(f"AUTO-UNLOCK: Task {dep_task.id} is now TODO")

    def create_task(self, user_id: int, task_data: dict[str, Any]) -> TaskEntity:
        """Create a new task."""
        # Create task through repository
        task = self.repository.create(user_id, task_data)
        return task

    def update_task(self, task_id: int, user_id: int, update_data: dict[str, Any]) -> TaskEntity:
        """Update an existing task."""
        # Get task
        task = self.repository.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        # Check if user owns the Task
        if task.user_id != user_id:
            raise ValueError("Task not found")

        # Update task
        return self.repository.update(task, update_data)

    def delete_task(self, task_id: int, user_id: int) -> None:
        """Delete a task."""
        # Get task
        task = self.repository.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        # Check if user owns the Task
        if task.user_id != user_id:
            raise ValueError("Task not found")

        # Delete task
        self.repository.delete(task_id)

    def get_user_tasks(self, user_id: int) -> list[TaskEntity]:
        """Get all tasks for a user."""
        return self.repository.get_by_user(user_id)

    def get_tasks_by_status(self, user_id: int, status: str) -> list[TaskEntity]:
        """Get tasks by status for a user."""
        return self.repository.filter_by_user_and_status(user_id, TaskStatus(status))
