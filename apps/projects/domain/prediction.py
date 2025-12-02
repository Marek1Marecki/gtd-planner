# apps/projects/domain/prediction.py
from datetime import date, timedelta
from typing import List
from apps.tasks.models import Task


class ProjectPredictor:
    def __init__(self, daily_capacity_minutes=240):  # Domyślnie 4h dziennie na projekty
        self.daily_capacity = daily_capacity_minutes

    def predict_completion_date(self, project_tasks) -> date:
        """
        Oblicza datę zakończenia na podstawie sumy czasów zadań.
        """
        # 1. Policz ile minut pracy zostało
        # (Bierzemy d_exp czyli średnią z min/max, lub default)
        total_minutes_left = 0
        for task in project_tasks:
            d_min = task.duration_min or 30
            d_max = task.duration_max or d_min
            d_exp = (d_min + d_max) / 2
            total_minutes_left += d_exp

        if total_minutes_left == 0:
            return date.today()

        # 2. Symulacja dni
        current_date = date.today()
        minutes_remaining = total_minutes_left

        while minutes_remaining > 0:
            # Przesuń na następny dzień
            current_date += timedelta(days=1)

            # Pomiń weekendy (Sobota=5, Niedziela=6)
            if current_date.weekday() >= 5:
                continue

            # "Wykonaj" pracę
            minutes_remaining -= self.daily_capacity

        return current_date