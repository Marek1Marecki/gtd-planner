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

        # 5. Bonus CPM (Critical Path Method)
        cpm_bonus = 0.0
        # Musimy dodać pole is_critical_path do TaskEntity! (zrób to w entities.py)
        if getattr(task, 'is_critical_path', False):
            cpm_bonus = 2.0  # Bardzo wysoki bonus!

        total_score = base_score + (self.weights['w_urgency'] * urgency_score) + cpm_bonus
        return round(total_score, 4)


class RecurrenceService:
    def generate_daily_instances(self) -> List[Task]:
        """Sprawdza aktywne szablony i generuje zadania na dziś."""
        today = date.today()
        generated = []

        # 1. Pobierz szablony, które mają termin <= dzisiaj
        patterns = RecurringPattern.objects.filter(
            is_active=True,
            next_run_date__lte=today,
            recurrence_type=RecurringPattern.RecurrenceType.FIXED
        )

        for pattern in patterns:
            # Sprawdź, czy nie ma już aktywnego zadania z tego szablonu (Anty-spam)
            active_exists = Task.objects.filter(
                recurring_pattern=pattern,
                status__in=[TaskStatus.TODO, TaskStatus.SCHEDULED, TaskStatus.OVERDUE]
            ).exists()

            if active_exists:
                continue  # Nie generuj duplikatu, dopóki stare wisi

            # 2. Utwórz instancję zadania
            new_task = Task.objects.create(
                user=pattern.user,
                title=pattern.title,
                project=pattern.project,
                priority=pattern.default_priority,
                duration_min=pattern.default_duration_min,
                duration_max=pattern.default_duration_min,  # uproszczenie
                status=TaskStatus.TODO,
                recurring_pattern=pattern,
                due_date=pattern.next_run_date  # Termin to data wygenerowania
            )
            generated.append(new_task)

            # 3. Przesuń datę następnego wykonania w szablonie
            pattern.next_run_date = pattern.next_run_date + timedelta(days=pattern.interval_days)
            pattern.save()

        return generated

    def handle_task_completion(self, task: Task):
        """Obsługa trybu DYNAMICZNEGO (po wykonaniu)."""
        pattern = task.recurring_pattern
        if not pattern:
            return

        if pattern.recurrence_type == RecurringPattern.RecurrenceType.DYNAMIC:
            # Ustaw następną datę relatywnie od DZISIAJ (bo dziś wykonano)
            today = date.today()
            pattern.next_run_date = today + timedelta(days=pattern.interval_days)
            pattern.save()
            # Uwaga: Nie generujemy zadania od razu.
            # Zostanie wygenerowane przez generate_daily_instances() gdy nadejdzie czas.