# apps/calendar_app/domain/services.py
from datetime import datetime, time, timedelta
from typing import List
from dataclasses import dataclass
from apps.calendar_app.ports.calendar_provider import FixedEvent
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.domain.services import TaskScorer


@dataclass
class ScheduledItem:
    task: TaskEntity
    start: datetime
    end: datetime


@dataclass
class FreeWindow:
    start: datetime
    end: datetime
    is_work: bool

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)


class SchedulerService:
    def calculate_free_windows(
        self,
        day_date: datetime.date,
        fixed_events: List[FixedEvent],
        work_start: time, # Zmieniamy na wymagane argumenty
        work_end: time
    ) -> List[FreeWindow]:
        """Dzieli dzień na wolne okna, omijając fixed_events."""

        # 1. Sortuj eventy chronologicznie
        fixed_events.sort(key=lambda e: e.start_time)

        # 2. Ustal ramy dnia (z uwzględnieniem strefy czasowej eventów)
        # Dla uproszczenia zakładamy UTC, w produkcji tz z usera
        import pytz
        tz = pytz.UTC

        # Pobierz godziny z profilu
        #work_start = user_profile.work_start_hour
        #work_end = user_profile.work_end_hour

        current_time = datetime.combine(day_date, work_start).replace(tzinfo=tz)
        end_of_day = datetime.combine(day_date, work_end).replace(tzinfo=tz)

        windows = []

        for event in fixed_events:
            # Jeśli event jest poza naszym oknem pracy, ignorujemy (uproszczenie)
            if event.end_time <= current_time:
                continue
            if event.start_time >= end_of_day:
                break

            # Jeśli jest luka przed eventem
            if event.start_time > current_time:
                windows.append(FreeWindow(
                    start=current_time,
                    end=event.start_time,
                    is_work=True  # Na razie tylko work
                ))

            # Przesuwamy kursor za event
            current_time = max(current_time, event.end_time)

        # Ostatnie okno po wszystkich eventach
        if current_time < end_of_day:
            windows.append(FreeWindow(
                start=current_time,
                end=end_of_day,
                is_work=True
            ))

        return windows

    def schedule_tasks(
        self,
        tasks: List[TaskEntity],
        windows: List[FreeWindow],
        now: datetime,
        user_profile  # Obiekt UserProfile z energy_profile
    ) -> List[ScheduledItem]:
        """
        Inteligentny algorytm alokacji (Bin Packing z priorytetami).
        Iteruje po oknach, dobierając zadania pasujące energetycznie i czasowo.
        """

        scorer = TaskScorer()
        schedule = []

        # Tworzymy kopię listy zadań do zaplanowania (żeby móc usuwać zaplanowane)
        # Filtrujemy tylko aktywne (TODO/SCHEDULED)
        remaining_tasks = [t for t in tasks if t.is_active()]

        for window in windows:
            current_time = window.start

            # Pobierz poziom energii dla danej godziny (uproszczenie: godzina startu okna)
            # Profil w bazie to np. { "09": 3, "10": 2 }
            current_hour_str = current_time.strftime("%H")

            # Domyślny poziom energii to 1 (Niska/Normalna), jeśli nie zdefiniowano
            slot_energy = 1
            if user_profile and user_profile.energy_profile:
                # JSON w bazie może mieć klucze jako stringi "09" lub inty 9.
                # Spróbujmy obu wariantów dla bezpieczeństwa.
                val = user_profile.energy_profile.get(current_hour_str)
                if val is None:
                    val = user_profile.energy_profile.get(int(current_hour_str))

                if val is not None:
                    slot_energy = int(val)

            # -----------------------------------------------------------
            # KROK 1: Przelicz Score dla tego konkretnego okna (Kontekst)
            # -----------------------------------------------------------
            scored_candidates = []
            for task in remaining_tasks:
                # Obliczamy score uwzględniając dopasowanie do slot_energy
                score = scorer.calculate_score(task, now, slot_energy_level=slot_energy)
                scored_candidates.append((task, score))

            # Sortuj malejąco po Score
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            # Tworzymy kolejkę priorytetową dla tego okna
            queue = [item[0] for item in scored_candidates]

            # -----------------------------------------------------------
            # KROK 2: Wypełnianie okna (Bin Packing)
            # -----------------------------------------------------------
            i = 0
            while i < len(queue):
                task = queue[i]
                duration = task.duration_expected

                # Ile czasu zostało w oknie?
                window_remaining_minutes = (window.end - current_time).total_seconds() / 60

                if duration <= window_remaining_minutes:
                    # Zadanie się mieści -> Planujemy!
                    end_time = current_time + timedelta(minutes=duration)

                    schedule.append(ScheduledItem(
                        task=task,
                        start=current_time,
                        end=end_time
                    ))

                    # Przesuwamy czas w oknie
                    current_time = end_time

                    # Zadanie zaplanowane: usuwamy z obu list (kolejki okna i głównej puli)
                    if task in remaining_tasks:
                        remaining_tasks.remove(task)

                    # Usuwamy z kolejki i NIE inkrementujemy 'i' (bo lista się przesunęła)
                    queue.pop(i)
                else:
                    # Zadanie się nie mieści -> sprawdzamy następne w kolejce (może krótsze wejdzie?)
                    i += 1

            # Koniec pętli dla danego okna. Przechodzimy do następnego okna.

        return schedule