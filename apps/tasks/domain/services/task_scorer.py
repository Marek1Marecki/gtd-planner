# apps/tasks/domain/services/task_scorer.py
from typing import List, Optional
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository
from datetime import date, datetime, timezone, timedelta
from apps.tasks.models import Task, RecurringPattern


class TaskScorer:
    def __init__(self, weights: dict = None):
        # Domyślne wagi, jeśli nie podano
        self.weights = weights or {
            'w_priority': 0.4,
            'w_duration': 0.3,
            'w_complexity': 0.3,
            'w_urgency': 1.5,
            'w_project_urgency': 1.0,
            'bonus_energy_match': 0.5,
            'bonus_sequence': 0.5,
            'w_goal_urgency': 1.0,
            'bonus_milestone': 2.0,  # Bardzo wysoki bonus!
        }

    def calculate_score(
            self,
            task: TaskEntity,
            now: datetime,
            slot_energy_level: int = 1,
            last_project_id: Optional[int] = None
        ) -> float:

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

        # ----------------------------------------------------
        # NOWY KOD: Bonus Energetyczny
        # ----------------------------------------------------
        energy_bonus = 0.0

        # Założenie: task.energy_required (1-3), slot_energy_level (1-3)
        # Jeśli wymagana energia <= dostępna energia -> Bonus!
        if task.energy_required <= slot_energy_level:
            # Im trudniejsze zadanie (wymaga więcej energii), tym większy bonus za dopasowanie
            # Np. Zrobienie trudnego zadania (3) w slocie (3) jest cenniejsze
            # niż zrobienie łatwego (1) w slocie (3).
            energy_bonus = self.weights['bonus_energy_match'] * (task.energy_required / 3.0)

        # Jeśli zadanie wymaga więcej niż mamy (np. 3 > 1), można dać karę (opcjonalnie)
        # elif task.energy_required > slot_energy_level:
        #     energy_bonus = -0.5

        # --- NOWE: Sequence Bonus ---
        seq_bonus = 0.0
        if last_project_id and task.project_id == last_project_id:
            # Jeśli to ten sam projekt -> Daj bonus
            seq_bonus = self.weights.get('bonus_sequence', 0.5)

            # Opcjonalnie: Tutaj można by dodać logikę "malejącego bonusu"
            # (diminishing returns), jeśli przekazalibyśmy licznik "k".
            # Na start stały bonus 0.5 jest wystarczający, by "przyciągnąć" kolegów.

        # --- NOWE: Goal Urgency ---
        goal_urgency = 0.0
        if task.goal_deadline:
            # Obsługa stref czasowych
            if task.goal_deadline.tzinfo is None and now.tzinfo:
                from django.utils.timezone import make_aware
                try:
                    target = make_aware(task.goal_deadline)
                except:
                    target = task.goal_deadline  # Fallback
            else:
                target = task.goal_deadline

            # Jeśli now ma strefę, a target nie (lub odwrotnie), zróbmy proste odejmowanie timestampów
            # Najprościej: operujmy na naive datetime lub obu aware.
            # Zakładamy że 'now' jest UTC aware.

            if target.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=timezone.utc)

            time_left = target - now
            days_left = time_left.total_seconds() / 86400

            # Wzór: Im bliżej (np. < 7 dni), tym wyższy bonus
            # Max bonus 1.0, jeśli deadline jest dzisiaj/jutro
            # 0.0 jeśli deadline > 14 dni
            if days_left <= 0:
                goal_urgency = 1.0
            elif days_left <= 14:
                goal_urgency = 1.0 - (days_left / 14.0)

        # --- NOWE: Project Urgency ---
        project_urgency_score = 0.0

        # Logika: Jeśli zadanie nie ma własnego deadline'u (lub chcemy wzmocnić przekaz),
        # sprawdzamy deadline projektu.
        # Wg specyfikacji: "Zadania bez własnego terminu dziedziczą presję".
        # Ale możemy dodać to addytywnie dla wszystkich, co jest bezpieczniejsze.

        if task.project_deadline:
            # Ujednolicenie stref czasowych (tak jak przy goal_deadline)
            target = task.project_deadline
            if target.tzinfo is None and now.tzinfo:
                # Zakładamy UTC dla uproszczenia lub konwertujemy
                pass

            if target.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=timezone.utc)

            time_left = target - now
            days_left = time_left.total_seconds() / 86400

            # Wzór na pilność projektu (łagodniejszy niż zadania)
            # Jeśli < 3 dni -> max bonus
            # Jeśli > 30 dni -> 0
            if days_left <= 0:
                project_urgency_score = 1.0
            elif days_left <= 14:
                project_urgency_score = 1.0 - (days_left / 14.0)

        # --- NOWE: Milestone Bonus ---
        milestone_bonus = 0.0
        if task.is_milestone:
            milestone_bonus = self.weights['bonus_milestone']

        # Sumowanie
        total_score = base_score + \
                      (self.weights['w_urgency'] * urgency_score) + \
                      (self.weights.get('w_goal_urgency', 1.0) * goal_urgency) + \
                      (self.weights['w_project_urgency'] * project_urgency_score) + \
                      energy_bonus + cpm_bonus + seq_bonus + milestone_bonus

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