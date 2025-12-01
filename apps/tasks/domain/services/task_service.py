# apps/tasks/domain/services.py
from typing import List
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository
from datetime import date, datetime, timezone, timedelta
from apps.tasks.models import Task, RecurringPattern


class TaskService:
    def __init__(self, repository: ITaskRepository):
        self.repository = repository

    def complete_task(self, task_id: int) -> TaskEntity:
        """Oznacza zadanie jako wykonane i uruchamia odblokowywanie."""

        # 1. Pobierz zadanie
        task = self.repository.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        # 2. Zmień status na DONE
        task.status = TaskStatus.DONE
        self.repository.save(task, user_id=None)  # user_id opcjonalny przy update

        # 3. Uruchom logikę AutoUnlock
        self._process_dependencies(task_id)

        return task

    def _process_dependencies(self, completed_task_id: int):
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

