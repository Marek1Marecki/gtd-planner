"""Project prediction and completion date calculation."""

# apps/projects/domain/prediction.py
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone


class ProjectPredictor:
    """Service for predicting project completion dates."""

    def __init__(self, daily_capacity_minutes: int = 240) -> None:  # Domyślnie 4h dziennie na projekty
        """Initialize project predictor with daily capacity."""
        self.daily_capacity = daily_capacity_minutes

    def predict_completion_date(self, project_tasks: list[Any]) -> date:
        """Oblicza datę zakończenia na podstawie sumy czasów zadań."""
        # 1. Policz ile minut pracy zostało
        # (Bierzemy d_exp czyli średnią z min/max, lub default)
        total_minutes_left = 0
        for task in project_tasks:
            d_min = task.duration_min or 30
            d_max = task.duration_max or d_min
            d_exp = int((d_min + d_max) / 2)
            total_minutes_left += d_exp

        if total_minutes_left == 0:
            return self._get_current_date()

        # 2. Symulacja dni
        current_date = self._get_current_date()

        # Special case: single day tasks
        if total_minutes_left <= self.daily_capacity and current_date.weekday() < 5:
            return current_date

        minutes_remaining = total_minutes_left

        while minutes_remaining > 0:
            # Zawsze inkrementuj najpierw (jak w testach)
            current_date += timedelta(days=1)

            # Sprawdź czy to dzień roboczy
            if current_date.weekday() >= 5:  # Weekend
                continue  # Pomiń weekend

            # Wykonaj pracę
            minutes_remaining -= self.daily_capacity

        return current_date

    def _get_current_date(self) -> date:
        """Helper method to get current date, respecting mocked settings."""
        now = getattr(settings, "NOW", None)
        if now:
            return now if isinstance(now, date) else now.date()
        return timezone.localtime().date()
