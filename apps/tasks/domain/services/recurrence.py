from datetime import date, timedelta
from typing import List
from apps.tasks.models import Task, RecurringPattern
from apps.tasks.domain.entities import TaskStatus


class RecurrenceService:
    def generate_daily_instances(self) -> List[Task]:
        """Sprawdza aktywne szablony i generuje zadania na dziś."""
        today = date.today()
        generated = []

        # Pobierz szablony, które mają termin <= dzisiaj
        patterns = RecurringPattern.objects.filter(
            is_active=True,
            next_run_date__lte=today,
            recurrence_type=RecurringPattern.RecurrenceType.FIXED
        )

        for pattern in patterns:
            # Sprawdź duplikaty
            active_exists = Task.objects.filter(
                recurring_pattern=pattern,
                status__in=[TaskStatus.TODO, TaskStatus.SCHEDULED, TaskStatus.OVERDUE]
            ).exists()

            if active_exists:
                continue

                # Utwórz instancję zadania
            new_task = Task.objects.create(
                user=pattern.user,
                title=pattern.title,
                project=pattern.project,
                priority=pattern.default_priority,
                duration_min=pattern.default_duration_min,
                duration_max=pattern.default_duration_min,
                status=TaskStatus.TODO,
                recurring_pattern=pattern,
                due_date=pattern.next_run_date
            )
            generated.append(new_task)

            # Statystyki i Data
            pattern.generated_count += 1
            pattern.next_run_date = pattern.next_run_date + timedelta(days=pattern.interval_days)
            pattern.save()

        return generated

    def handle_task_completion(self, task: Task):
        """Obsługa trybu DYNAMICZNEGO (po wykonaniu)."""
        pattern = task.recurring_pattern
        if not pattern:
            return

        if pattern.recurrence_type == RecurringPattern.RecurrenceType.DYNAMIC:
            today = date.today()
            pattern.next_run_date = today + timedelta(days=pattern.interval_days)
            pattern.save()