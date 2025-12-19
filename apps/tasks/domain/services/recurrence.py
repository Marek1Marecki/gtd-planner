#apps/tasks/domain/services/recurrence.py
from datetime import date, datetime, timedelta
from typing import List
from dateutil.rrule import rrulestr
from django.utils import timezone
from apps.tasks.models import Task, RecurringPattern
from apps.tasks.domain.entities import TaskStatus
from apps.tasks.models import ChecklistItem


class RecurrenceService:
    def generate_daily_instances(self) -> List[Task]:
        """Sprawdza aktywne szablony (Fixed) i generuje zadania na dziś."""
        today = date.today()
        generated = []

        # Pobierz szablony FIXED, które mają termin <= dzisiaj
        patterns = RecurringPattern.objects.filter(
            is_active=True,
            is_dynamic=False,  # Tylko sztywne (kalendarzowe)
            next_run_date__lte=today
        )

        for pattern in patterns:
            # 1. Sprawdź warunki końca (End Date / Max Occurrences)
            if pattern.end_date and pattern.end_date < today:
                pattern.is_active = False
                pattern.save()
                continue

            if pattern.max_occurrences and pattern.generated_count >= pattern.max_occurrences:
                pattern.is_active = False
                pattern.save()
                continue

            # 2. Sprawdź duplikaty (czy już nie wygenerowano na dziś)
            # To ważne przy rrule, żeby nie spamować
            active_exists = Task.objects.filter(
                recurring_pattern=pattern,
                due_date=pattern.next_run_date,  # Sprawdzamy konkretną datę
                status__in=[TaskStatus.TODO, TaskStatus.SCHEDULED, TaskStatus.OVERDUE, TaskStatus.DONE]
            ).exists()

            if active_exists:
                # Jeśli zadanie na tę datę już jest, to tylko przeliczamy następną datę (naprawa stanu)
                self._update_next_run_date(pattern)
                continue

                # 3. Utwórz instancję zadania
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
            # --- NOWE: Kopiowanie Checklisty ---
            # Pobierz punkty z szablonu
            template_items = pattern.template_items.all()
            for item in template_items:
                # Utwórz kopię dla nowego zadania
                # WAŻNE: is_completed=False (resetujemy ptaszki!)
                ChecklistItem.objects.create(
                    task=new_task,
                    text=item.text,
                    order=item.order,
                    is_completed=False
                )
            # -----------------------------------
            generated.append(new_task)

            # Statystyki
            pattern.generated_count += 1

            # 4. Oblicz następną datę używając RRULE
            self._update_next_run_date(pattern)

        return generated

    def handle_task_completion(self, task: Task):
        """Obsługa trybu DYNAMICZNEGO (po wykonaniu)."""
        pattern = task.recurring_pattern
        if not pattern or not pattern.is_dynamic:
            return

        # W trybie dynamicznym "następny raz" to DZISIAJ + INTERWAŁ
        # Tutaj RRULE nie jest potrzebne, wystarczy prosta matematyka
        # Chyba że chcemy "Dzisiaj + 3 dni, ale tylko w Robocze" - wtedy RRULE.
        # Dla uproszczenia (zgodnie z obrazkiem): "X days/weeks after completed"

        today = date.today()
        # Prosta logika: Data wykonania + Interval
        if pattern.frequency == 'WEEKLY':
            delta = timedelta(weeks=pattern.interval)
        elif pattern.frequency == 'MONTHLY':
            delta = timedelta(days=30 * pattern.interval)  # Uproszczenie
        else:  # DAILY
            delta = timedelta(days=pattern.interval)

        pattern.next_run_date = today + delta
        pattern.save()

    def _update_next_run_date(self, pattern: RecurringPattern):
        """Używa dateutil.rrule do wyznaczenia następnej daty kalendarzowej."""
        try:
            # Budujemy string RRULE
            rrule_str = pattern.get_rrule_string()

            # Musimy dodać DTSTART, żeby rrule wiedziało od kiedy liczyć
            # Używamy dzisiejszej daty jako punktu odniesienia, żeby znaleźć *przyszłe* wystąpienie
            # Albo używamy created_at jako startu.
            # Najbezpieczniej: DTSTART = today

            dtstart = f"DTSTART:{datetime.now().strftime('%Y%m%dT%H%M%S')}"
            full_rule = f"{dtstart}\nRRULE:{rrule_str}"

            # Wyznaczamy terminy
            rule = rrulestr(full_rule)

            # Bierzemy pierwsze wystąpienie PO dzisiejszym dniu (lub po obecnym next_run_date)
            # after() zwraca datetime
            next_date = rule.after(datetime.combine(pattern.next_run_date, datetime.min.time()))

            if next_date:
                pattern.next_run_date = next_date.date()
                pattern.save()
            else:
                # Koniec cyklu (np. limit wystąpień)
                pattern.is_active = False
                pattern.save()

        except Exception as e:
            print(f"Błąd RRULE dla {pattern.title}: {e}")