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