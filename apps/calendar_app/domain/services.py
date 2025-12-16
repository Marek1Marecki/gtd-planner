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
        user_profile  # Obiekt UserProfile
    ) -> List[ScheduledItem]:
        """
        Inteligentny algorytm alokacji (Bin Packing) z pełnym scoringiem.
        Uwzględnia: Priorytet, Energię, Ciągłość (Sequence) i Presję Końca Dnia (EOD).
        """

        scorer = TaskScorer()
        schedule = []

        # Kopia listy zadań
        remaining_tasks = [t for t in tasks if t.is_active()]

        # Stan Schedulera
        last_project_id = None
        sequence_count = 0

        # Ustal koniec dnia dla tego przebiegu (ostatni moment ostatniego okna)
        absolute_end_time = now
        if windows:
            absolute_end_time = windows[-1].end

        for window in windows:
            current_time = window.start

            # Poziom Energii Okna
            current_hour_str = current_time.strftime("%H")
            slot_energy = 1
            if user_profile and user_profile.energy_profile:
                val = user_profile.energy_profile.get(current_hour_str)
                if val is None:
                    val = user_profile.energy_profile.get(int(current_hour_str))
                if val is not None:
                    slot_energy = int(val)

            # Pętla Alokacji w Oknie
            while remaining_tasks and (window.end - current_time).total_seconds() > 0:

                # Oblicz czas do końca dnia (EOD Factor)
                time_to_end = absolute_end_time - current_time
                hours_to_end = time_to_end.total_seconds() / 3600

                # 1. Scoring
                scored_candidates = []
                for task in remaining_tasks:
                    score = scorer.calculate_score(
                        task,
                        now,
                        slot_energy_level=slot_energy,
                        last_project_id=last_project_id,
                        sequence_count=sequence_count,
                        hours_to_end_of_day=hours_to_end  # <-- EOD Factor
                    )
                    scored_candidates.append((task, score))

                # Sortuj malejąco po: 1. Score, 2. Odwróconym czasie (krótsze mają wyższy priorytet przy remisie)
                scored_candidates.sort(key=lambda x: (x[1], -x[0].duration_expected), reverse=True)

                # 2. Wybór (Bin Packing)
                best_candidate = None
                window_remaining_minutes = (window.end - current_time).total_seconds() / 60

                for task, score in scored_candidates:
                    if task.duration_expected <= window_remaining_minutes:
                        best_candidate = task
                        break

                if best_candidate:
                    # Planujemy
                    end_time = current_time + timedelta(minutes=best_candidate.duration_expected)

                    schedule.append(ScheduledItem(
                        task=best_candidate,
                        start=current_time,
                        end=end_time
                    ))

                    current_time = end_time
                    remaining_tasks.remove(best_candidate)

                    # Aktualizacja Sequence
                    if best_candidate.project_id and best_candidate.project_id == last_project_id:
                        sequence_count += 1
                    else:
                        sequence_count = 0

                    last_project_id = best_candidate.project_id
                else:
                    # Nikt się nie mieści w tym oknie
                    break

        return schedule