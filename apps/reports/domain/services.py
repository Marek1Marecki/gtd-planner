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