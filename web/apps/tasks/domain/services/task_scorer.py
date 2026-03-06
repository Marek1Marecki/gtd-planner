"""Task scoring services for prioritization."""

# apps/tasks/domain/services/task_scorer.py
from datetime import UTC, date, datetime

from apps.tasks.domain.entities import TaskEntity


class TaskScorer:
    """Service for scoring and prioritizing tasks."""

    def __init__(self, weights: dict[str, float] | None = None):
        """Initialize task scorer with custom weights."""
        # Domyślne wagi, jeśli nie podano
        self.weights = weights or {
            "w_priority": 0.4,
            "w_duration": 0.3,
            "w_complexity": 0.3,
            "w_urgency": 1.5,
            "w_project_urgency": 1.0,
            "bonus_energy_match": 0.5,
            "bonus_sequence": 0.5,
            "w_goal_urgency": 1.0,
            "bonus_milestone": 2.0,  # Bardzo wysoki bonus!
        }

    def calculate_score(
        self,
        task: TaskEntity,
        now: datetime,
        slot_energy_level: int = 1,
        last_project_id: int | None = None,
        sequence_count: int = 0,
        hours_to_end_of_day: float | None = None,
    ) -> float:
        """Calculate priority score for a task."""
        # 1. Normalizacja Priorytetu (skala 1-5 -> 0.0-1.0)
        # priority=1 to najwyższy, więc odwracamy skalę
        norm_priority = (5 - task.priority) / 4.0

        # 2. Normalizacja Czasu
        d_exp = task.duration_expected
        max_duration = 240.0
        norm_duration = max(0.0, 1.0 - (d_exp / max_duration))

        # 3. Normalizacja Złożoności
        norm_complexity = 1.0 - ((task.complexity - 1) / 4.0)

        # Obliczamy wynik bazowy (musi być tutaj, przed użyciem w total_score)
        base_score = (
            self.weights["w_priority"] * norm_priority
            + self.weights["w_duration"] * norm_duration
            + self.weights["w_complexity"] * norm_complexity
        )

        # 4. Urgency (Pilność)
        urgency_score = 0.0
        if task.due_date:
            # Konwertuj date na datetime jeśli potrzebne
            if isinstance(task.due_date, date) and not isinstance(task.due_date, datetime):
                task_due = datetime.combine(task.due_date, datetime.min.time())
                if now.tzinfo:
                    task_due = task_due.replace(tzinfo=UTC)
            else:
                task_due = task.due_date

            # Obsługa stref czasowych
            if task_due.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=UTC)

            # Oblicz różnicę czasu
            time_left = task_due - now
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
        if getattr(task, "is_critical_path", False):
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
            energy_bonus = self.weights["bonus_energy_match"] * (task.energy_required / 3.0)

        # Jeśli zadanie wymaga więcej niż mamy (np. 3 > 1), można dać karę (opcjonalnie)
        # elif task.energy_required > slot_energy_level:
        #     energy_bonus = -0.5

        # --- NOWE: Goal Urgency ---
        goal_urgency = 0.0
        if task.goal_deadline:
            # Obsługa stref czasowych (tylko stdlib)
            if task.goal_deadline.tzinfo is None and now.tzinfo:
                target = task.goal_deadline.replace(tzinfo=UTC)
            else:
                target = task.goal_deadline

            # Jeśli now ma strefę, a target nie (lub odwrotnie), zróbmy proste odejmowanie timestampów
            # Najprościej: operujmy na naive datetime lub obu aware.
            # Zakładamy że 'now' jest UTC aware.

            if target.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=UTC)

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
                now = now.replace(tzinfo=UTC)

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
            milestone_bonus = self.weights["bonus_milestone"]

        # --- NOWE: Sequence Bonus ---
        seq_bonus = 0.0
        if last_project_id and task.project_id == last_project_id:
            # Prosty bonus za ciągłość - nie malejący
            seq_bonus = self.weights.get("bonus_sequence", 0.5)

        # --- AGING BONUS ---
        aging_bonus = 0.0

        # Używamy ready_since, a jak brak (np. stare zadania), to fallback do created_at (lub 0)
        start_time = (
            task.ready_since if task.ready_since else task.created_at
        )  # Tutaj w Entity musisz mieć też created_at

        # Jeśli nadal None (np. zadanie jest blocked), bonus = 0
        if start_time:
            if start_time.tzinfo is None and now.tzinfo:
                now = now.replace(tzinfo=UTC)

            wait_time = now - start_time
            hours_waiting = wait_time.total_seconds() / 3600

            # Wzór: max bonus po 72h (3 dni) - przykładowo
            max_wait_hours = 72.0
            if hours_waiting > 0:
                aging_bonus = 1.0 * min(1.0, hours_waiting / max_wait_hours)

        # --- End of Day (EOD) Factor ---
        eod_bonus = 0.0

        if hours_to_end_of_day is not None and hours_to_end_of_day < 2.0:
            # Jesteśmy w "strefie śmierci" (ostatnie 2h dnia)

            # 1. Promuj zadania krótkie (<= 30 min)
            if task.duration_expected <= 30:
                eod_bonus += 0.5

            # 2. Promuj zadania z dzisiejszym deadline (Last Minute)
            if task.due_date:
                # Sprawdź czy deadline jest dziś
                # (Uproszczenie: porównujemy daty, zakładając zgodność stref)
                if task.due_date.date() <= now.date():
                    eod_bonus += 1.0

            # 3. Zniechęcaj do zadań trudnych (Mental Fatigue)
            if task.complexity >= 4:
                eod_bonus -= 0.5

        # Sumowanie
        total_score = (
            base_score
            + (self.weights["w_urgency"] * urgency_score)
            + (1.0 * goal_urgency)
            + (1.0 * project_urgency_score)
            + energy_bonus
            + cpm_bonus
            + milestone_bonus
            + seq_bonus
            + aging_bonus
            + eod_bonus
        )

        return round(total_score, 4)

    @staticmethod
    def get_weights_for_strategy(strategy_name: str) -> dict[str, float]:
        """Zwraca zestaw wag dla danej strategii."""
        # Wagi domyślne (Balanced)
        defaults = {
            "w_priority": 0.4,
            "w_duration": 0.3,
            "w_complexity": 0.3,
            "w_urgency": 1.5,
            "w_goal_urgency": 1.0,
            "w_project_urgency": 1.0,
            "bonus_sequence": 0.5,
            "bonus_energy_match": 0.5,
            "bonus_milestone": 2.0,
        }

        if strategy_name == "warmup":
            # Rozgrzewka: Promuj zadania proste (complexity) i krótkie (duration)
            # Ignoruj priorytet (chcemy się rozkręcić, a nie robić ważne rzeczy)
            return {**defaults, "w_complexity": 0.8, "w_duration": 0.6, "w_priority": 0.1}

        elif strategy_name == "deep_work":
            # Głęboka praca: Bardzo wysoki bonus za ciągłość projektu
            return {**defaults, "bonus_sequence": 2.5}

        elif strategy_name == "deadline":
            # Tryb awaryjny: Liczą się tylko terminy (Urgency)
            return {
                **defaults,
                "w_urgency": 3.0,
                "w_goal_urgency": 2.0,
                "w_project_urgency": 2.0,
                "w_complexity": 0.0,  # Trudność nie ma znaczenia, trzeba dowieźć
            }

        return defaults
