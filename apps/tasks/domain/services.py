# apps/tasks/domain/services.py
from typing import List
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository
from datetime import datetime, timezone


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


class TaskScorer:
    def __init__(self, weights: dict = None):
        # Domyślne wagi, jeśli nie podano
        self.weights = weights or {
            'w_priority': 0.4,
            'w_duration': 0.3,
            'w_complexity': 0.3,
            'w_urgency': 1.5,
        }

    def calculate_score(self, task: TaskEntity, now: datetime) -> float:
        # 1. Normalizacja Priorytetu (skala 1-5 -> 0.0-1.0)
        norm_priority = (task.priority - 1) / 4.0

        # 2. Normalizacja Czasu
        d_exp = task.duration_expected
        max_duration = 240.0
        norm_duration = max(0.0, 1.0 - (d_exp / max_duration))

        # 3. Normalizacja Złożoności
        norm_complexity = 1.0 - ((task.complexity - 1) / 4.0)

        # Obliczamy wynik bazowy (musi być tutaj, przed użyciem w total_score)
        base_score = (
            self.weights['w_priority'] * norm_priority +
            self.weights['w_duration'] * norm_duration +
            self.weights['w_complexity'] * norm_complexity
        )

        # 4. Urgency (Pilność)
        urgency_score = 0.0
        if task.due_date:
            # Obsługa stref czasowych
            if task.due_date.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=timezone.utc)

            # Oblicz różnicę czasu
            time_left = task.due_date - now
            hours_left = time_left.total_seconds() / 3600

            if hours_left <= 0:
                # OVERDUE!
                urgency_score = 2.0
            elif hours_left <= 24:
                # < 24h
                urgency_score = 1.0 + (1.0 - (hours_left / 24.0))
            elif hours_left <= 72:
                # < 3 dni
                urgency_score = 0.5 * (1.0 - ((hours_left - 24) / 48.0))
            else:
                urgency_score = 0.1

        # Sumowanie
        total_score = base_score + (self.weights['w_urgency'] * urgency_score)

        return round(total_score, 4)