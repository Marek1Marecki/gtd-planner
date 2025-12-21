# apps/reports/domain/services.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from apps.reports.models import ActivityLog
from apps.tasks.models import Task


class ReportService:

    def get_weekly_stats(self, user):
        """Zwraca statystyki z ostatnich 7 dni."""
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        # 1. Ile zadań ukończono?
        completed_count = ActivityLog.objects.filter(
            user=user,
            action_type=ActivityLog.ActionType.COMPLETED,
            timestamp__gte=week_ago
        ).count()

        # 2. Ile zadań dodano?
        created_count = ActivityLog.objects.filter(
            user=user,
            action_type=ActivityLog.ActionType.CREATED,
            timestamp__gte=week_ago
        ).count()

        # 3. Stan obecny (Snapshot)
        status_breakdown = Task.objects.filter(user=user).values('status').annotate(total=Count('status'))

        return {
            'period': 'Last 7 Days',
            'completed': completed_count,
            'created': created_count,
            'velocity': completed_count / 7.0,  # zadania na dzień
            'breakdown': {item['status']: item['total'] for item in status_breakdown}
        }


    def get_area_distribution(self, user):
        """Zwraca liczbę zadań per Area (dla aktywnych zadań)."""
        from apps.tasks.models import Task
        from django.db.models import Count

        # Grupuj po nazwie obszaru i kolorze
        data = Task.objects.filter(user=user, status__in=['todo', 'scheduled', 'done']) \
            .values('area__name', 'area__color') \
            .annotate(count=Count('id'))

        # Formatowanie dla Chart.js
        labels = []
        counts = []
        colors = []

        for item in data:
            name = item['area__name'] or "Bez obszaru"
            color = item['area__color'] or "#cccccc"
            labels.append(name)
            counts.append(item['count'])
            colors.append(color)

        return {'labels': labels, 'data': counts, 'colors': colors}


    def get_habit_stats(self, user):
        """Zwraca skuteczność nawyków w ostatnich 30 dniach."""
        from apps.habits.models import Habit, HabitLog

        habits = Habit.objects.filter(user=user, is_active=True)
        stats = []

        # Zakres: ostatnie 30 dni
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        days_count = 30

        for h in habits:
            # Ile razy wykonano w tym okresie?
            logs_count = HabitLog.objects.filter(
                habit=h,
                date__gte=start_date
            ).count()

            # Prosta skuteczność (logs / 30 dni) * 100
            # (Dla nawyków 'co 2 dni' to będzie max 50%, ale dla codziennych działa dobrze)
            rate = int((logs_count / days_count) * 100)

            stats.append({
                'title': h.title,
                'streak': h.current_streak,
                'rate_30d': rate
            })

        return stats


    def get_recurring_health(self, user):
        """Zwraca średnie opóźnienie dla zadań cyklicznych."""
        from apps.tasks.models import RecurringPattern, Task
        from django.db.models import F, Avg

        patterns = RecurringPattern.objects.filter(user=user, is_active=True)
        stats = []

        for pat in patterns:
            # Pobierz zadania ukończone
            # Oblicz delay: completed_at - due_date
            # To trudne w czystym ORM SQLite/Postgres bez funkcji DB,
            # więc zrobimy to w Pythonie (na małej próbce np. 5 ostatnich).

            tasks = Task.objects.filter(recurring_pattern=pat, status='done').order_by('-completed_at')[:5]
            if not tasks: continue

            delays = []
            for t in tasks:
                if t.due_date and t.completed_at:
                    # completed_at to datetime, due_date to date (lub datetime)
                    # Ujednolicamy do date()
                    delta = (t.completed_at.date() - t.due_date.date()).days
                    delays.append(max(0, delta))  # 0 jeśli przed czasem

            avg_delay = sum(delays) / len(delays) if delays else 0

            stats.append({
                'title': pat.title,
                'avg_delay': round(avg_delay, 1),
                'rate': pat.completion_rate,
                'total': pat.generated_count
            })

        return stats


    def get_context_distribution(self, user):
        """Zwraca liczbę zadań per Context."""
        from apps.tasks.models import Task
        from django.db.models import Count

        # Grupuj po nazwie kontekstu
        data = Task.objects.filter(user=user, status__in=['todo', 'scheduled', 'done']) \
            .values('context__name', 'context__color') \
            .annotate(count=Count('id'))

        labels = []
        counts = []
        colors = []

        for item in data:
            name = item['context__name'] or "Bez kontekstu"
            color = item['context__color'] or "#6c757d"  # Szary domyślny
            labels.append(name)
            counts.append(item['count'])
            colors.append(color)

        return {'labels': labels, 'data': counts, 'colors': colors}


    def get_blocking_chains(self, user):
        """
        Zwraca listę 'łańcuchów': Zadania aktywne, które blokują inne zadania.
        Struktura: [{ 'root': task, 'blocked_children': [task, task...] }]
        """
        from apps.tasks.models import Task

        # 1. Znajdź zadania, które są blokerami (są w polu blocked_by innych zadań)
        # i same są aktywne (TODO/SCHEDULED).
        # To są nasze "Korki".

        blockers = Task.objects.filter(
            user=user,
            status__in=['todo', 'scheduled'],
            blocking__status='blocked'  # blocking to related_name dla 'blocked_by' (zdefiniowane w modelu Task?)
        ).distinct()

        # Sprawdźmy related_name w modelu Task.
        # W kroku 2.5 (Faza 2) zdefiniowaliśmy: related_name='blocking'.

        chains = []
        for root in blockers:
            # Znajdź zadania, które ten root bezpośrednio blokuje
            children = root.blocking.filter(status='blocked')

            if children.exists():
                chains.append({
                    'root': root,
                    'children': children
                })

        return chains

    def get_productivity_heatmap(self, user):
        """
        Generuje heatmapę godzinową (0-23) obciążenia pracą.
        Uwzględnia duration i energy zadania (Back-filling).
        """
        from apps.reports.models import ActivityLog
        from apps.tasks.models import Task

        # Inicjalizacja wiaderek (0-23h)
        # hourly_load[14] = suma punktów obciążenia o 14:00
        hourly_load = [0] * 24

        # Zakres: ostatnie 30 dni
        month_ago = timezone.now() - timedelta(days=30)

        # Pobierz logi ukończenia
        # Optymalizacja: select_related nie zadziała dla GenericForeignKey w prosty sposób,
        # więc pobieramy logi, a potem zadania w pętli (dla 30 dni to akceptowalne w MVP)
        # LUB: Pobieramy zadania DONE z updated_at > 30 dni (szybciej)

        tasks = Task.objects.filter(
            user=user,
            status='done',
            # Używamy completed_at jeśli jest, lub updated_at
            # Zakładamy, że completed_at zostało wdrożone w poprzedniej fazie
        )

        for task in tasks:
            # Data ukończenia
            end_time = task.completed_at or task.updated_at
            if not end_time or end_time < month_ago:
                continue

            # Ustal duration (minuty)
            duration = task.duration_expected
            if not duration or duration < 5: duration = 30  # Default dla zadań bez czasu

            # Ustal energię (mnożnik)
            # Energy: 1 (Low), 2 (Mid), 3 (High)
            energy_mult = task.energy_required or 1

            # Algorytm Back-filling
            # Symulujemy pracę wstecz od end_time
            current_time = end_time
            minutes_left = duration

            while minutes_left > 0:
                # Która to godzina? (0-23)
                hour_idx = current_time.hour

                # Ile minut w tej godzinie zajęło zadanie?
                # Np. jest 14:15. Do początku godziny (14:00) jest 15 min.
                minutes_in_hour = current_time.minute

                # Jeśli zadanie trwało krócej niż to co upłynęło w godzinie
                step = min(minutes_left, minutes_in_hour)

                # Jeśli step == 0 (np. jest 14:00:00), cofamy się do poprzedniej godziny 13:59
                if step == 0:
                    current_time -= timedelta(minutes=1)
                    continue

                # Dodaj punkty do wiaderka
                # Punkty = Minuty * Energia
                hourly_load[hour_idx] += step * energy_mult

                # Odejmij czas
                minutes_left -= step
                current_time -= timedelta(minutes=step)

        # Normalizacja wyników (opcjonalnie, żeby wykres był czytelny)
        # Zwracamy surowe punkty, Chart.js sobie poradzi
        return hourly_load