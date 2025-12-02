from datetime import date, timedelta
from .models import Habit, HabitLog


class HabitService:
    def complete_habit(self, habit: Habit, day: date):
        # 1. Sprawdź czy już nie zrobione dzisiaj
        if HabitLog.objects.filter(habit=habit, date=day).exists():
            return  # Już zrobione

        # 2. Utwórz log
        HabitLog.objects.create(habit=habit, date=day)

        # 3. Oblicz Streak
        # Jeśli ostatnie wykonanie było wczoraj -> streak++
        # Jeśli ostatnie wykonanie było dzisiaj -> nic
        # Jeśli dawniej -> reset do 1

        yesterday = day - timedelta(days=1)

        if habit.last_completed_date == yesterday:
            habit.current_streak += 1
        elif habit.last_completed_date == day:
            pass  # Nic nie rób, to dubel
        else:
            habit.current_streak = 1  # Reset (lub start)

        # Update max streak
        if habit.current_streak > habit.longest_streak:
            habit.longest_streak = habit.current_streak

        habit.last_completed_date = day
        habit.save()