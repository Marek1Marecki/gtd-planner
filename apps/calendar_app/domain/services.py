# apps/calendar_app/domain/services.py
from datetime import date, datetime, timedelta, timezone, time
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

    def get_weekly_plan(self, user, start_date: date):
        """Generuje plan na 7 dni od start_date."""
        from apps.calendar_app.adapters.google_calendar import GoogleCalendarAdapter
        from apps.tasks.adapters.orm_repositories import DjangoTaskRepository

        week_plan = []
        days = [start_date + timedelta(days=i) for i in range(7)]
        end_date = days[-1]

        # 1. Pobierz zadania (pula do rozdysponowania)
        task_repo = DjangoTaskRepository()
        all_tasks = task_repo.get_active_tasks()
        # Ważne: Kopiujemy listę, bo scheduler będzie ją "zjadał" (usuwał zaplanowane)
        # Ale tutaj chcemy symulację. Jeśli zadanie zaplanujemy w Poniedziałek,
        # to we Wtorek już nie powinno być dostępne.
        # Nasz `schedule_tasks` nie modyfikuje obiektów w bazie, więc musimy
        # sami zarządzać pulą `remaining_tasks` między dniami.

        pool_work = [t for t in all_tasks if not t.is_private]
        pool_personal = [t for t in all_tasks if t.is_private]

        # 2. Pobierz Fixed Events (Batch)
        gcal = GoogleCalendarAdapter()
        all_fixed = gcal.get_events_range(user.id, start_date, end_date)

        # 3. Pętla po dniach
        for day in days:
            # Filtruj fixed events dla tego dnia
            day_fixed = [e for e in all_fixed if e.start_time.date() == day]

            # Profil (Godziny) - dla uproszczenia te same co w user profile,
            # ale w weekendy mogłyby być inne (TODO).
            try:
                profile = user.profile
            except:
                continue

            now = datetime.now(timezone.utc)  # Używane tylko do oceny "czy już po czasie"

            # --- Work Timeline ---
            work_wins = self.calculate_free_windows(day, day_fixed, profile.work_start_hour, profile.work_end_hour)
            work_sched = self.schedule_tasks(pool_work, work_wins, now, profile)

            # Usuń zaplanowane z puli (żeby nie planować ich znowu jutro)
            scheduled_ids = {item.task.id for item in work_sched}
            pool_work = [t for t in pool_work if t.id not in scheduled_ids]

            # --- Personal Timeline ---
            pers_wins = self.calculate_free_windows(day, day_fixed, profile.personal_start_hour,
                                                    profile.personal_end_hour)
            pers_sched = self.schedule_tasks(pool_personal, pers_wins, now, profile)

            scheduled_ids_p = {item.task.id for item in pers_sched}
            pool_personal = [t for t in pool_personal if t.id not in scheduled_ids_p]

            # Zapisz wynik dnia
            week_plan.append({
                'date': day,
                'day_name': day.strftime("%A"),  # np. Monday
                'items': work_sched + pers_sched + day_fixed  # Tylko do wyświetlania
                # Uwaga: day_fixed ma inną strukturę niż ScheduledItem, trzeba uważać w szablonie
            })

        return week_plan