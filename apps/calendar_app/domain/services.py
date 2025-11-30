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
        work_start: time = time(9, 0),
        work_end: time = time(17, 0)
    ) -> List[FreeWindow]:
        """Dzieli dzień na wolne okna, omijając fixed_events."""

        # 1. Sortuj eventy chronologicznie
        fixed_events.sort(key=lambda e: e.start_time)

        # 2. Ustal ramy dnia (z uwzględnieniem strefy czasowej eventów)
        # Dla uproszczenia zakładamy UTC, w produkcji tz z usera
        import pytz
        tz = pytz.UTC

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
        now: datetime
    ) -> List[ScheduledItem]:
        """Algorytm Bin Packing z priorytetami."""

        scorer = TaskScorer()
        schedule = []

        # 1. Oblicz Score dla każdego zadania
        # (W prawdziwym kodzie robilibyśmy to wewnątrz pętli okien dla Energy Bonus,
        # ale dla MVP zróbmy to raz globalnie)
        scored_tasks = []
        for t in tasks:
            if not t.is_active(): continue
            score = scorer.calculate_score(t, now)
            scored_tasks.append((t, score))

        # 2. Sortuj malejąco po Score
        scored_tasks.sort(key=lambda x: x[1], reverse=True)

        # Lista zadań do zaplanowania (kolejka)
        queue = [item[0] for item in scored_tasks]

        # 3. Pętla Alokacji
        for window in windows:
            current_time = window.start

            # Dopóki jest czas w oknie i są zadania w kolejce
            i = 0
            while i < len(queue):
                task = queue[i]
                duration = task.duration_expected

                # Sprawdź czy się mieści
                window_remaining = (window.end - current_time).total_seconds() / 60

                if duration <= window_remaining:
                    # Pasuje! Planujemy.
                    end_time = current_time + timedelta(minutes=duration)

                    schedule.append(ScheduledItem(
                        task=task,
                        start=current_time,
                        end=end_time
                    ))

                    # Przesuwamy czas w oknie
                    current_time = end_time

                    # Usuwamy zadanie z kolejki (zrobione)
                    queue.pop(i)
                    # Nie inkrementujemy 'i', bo lista się skróciła
                else:
                    # Nie mieści się - szukamy dalej w kolejce (może jest krótsze zadanie?)
                    i += 1

            # Koniec okna

        return schedule