# apps/tasks/domain/services/tickler.py
from datetime import date
from django.db.models import Q
from apps.tasks.models import Task, TaskStatus


class TicklerService:
    def get_tasks_for_review(self, user):
        """
        Zwraca zadania, które wymagają uwagi dzisiaj.
        Warunki:
        1. Status to WAITING/DELEGATED/POSTPONED
        2. review_date <= dzisiaj (lub brak daty, jeśli chcemy być surowi)
        """
        today = date.today()

        # Zapytanie ORM (Adapter)
        # Szukamy zadań "wstrzymanych", których termin przeglądu nadszedł
        return Task.objects.filter(
            user=user,
            status__in=['waiting', 'delegated', 'postponed'],
            review_date__lte=today
        ).order_by('review_date')


    def get_stale_waiting_tasks(self, user, days=3):
        """Zwraca zadania waiting bez daty przeglądu, które wiszą dłużej niż X dni."""
        from django.utils import timezone
        threshold = timezone.now() - timezone.timedelta(days=days)

        return Task.objects.filter(
            user=user,
            status='waiting',
            review_date__isnull=True,
            updated_at__lte=threshold
        )