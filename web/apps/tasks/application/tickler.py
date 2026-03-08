"""Tickler services for task review management."""

# apps/tasks/domain/services/tickler.py
from datetime import date, timedelta
from typing import Any

from apps.tasks.models import Task


class TicklerService:
    """Service for managing tickler file and task reviews."""

    def get_tasks_for_review(self, user: Any) -> Any:
        """Zwraca zadania, które wymagają uwagi dzisiaj.

        Warunki:
        1. Status to WAITING/DELEGATED/POSTPONED
        2. review_date <= dzisiaj (lub brak daty, jeśli chcemy być surowi)
        """
        today = date.today()

        # Zapytanie ORM (Adapter)
        # Szukamy zadań "wstrzymanych", których termin przeglądu nadszedł
        return Task.objects.filter(
            user=user, status__in=["waiting", "delegated", "postponed"], review_date__lte=today
        ).order_by("review_date")

    def get_stale_waiting_tasks(self, user: Any, days: int = 3) -> Any:
        """Zwraca zadania waiting bez daty przeglądu, które wiszą dłużej niż X dni."""
        from django.utils import timezone

        threshold = timezone.now() - timedelta(days=days)

        return Task.objects.filter(user=user, status="waiting", review_date__isnull=True, updated_at__lte=threshold)
