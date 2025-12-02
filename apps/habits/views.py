from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import date
from .models import Habit, HabitLog
from .services import HabitService


@login_required
def habit_list_widget(request):
    """Zwraca widget z listą nawyków na dziś."""
    habits = Habit.objects.filter(user=request.user, is_active=True)
    today = date.today()

    # Oznacz, które są zrobione dzisiaj
    completed_ids = set(HabitLog.objects.filter(
        habit__in=habits, date=today
    ).values_list('habit_id', flat=True))

    for h in habits:
        h.is_completed_today = h.id in completed_ids

    return render(request, 'habits/partials/widget.html', {'habits': habits})


@login_required
@require_POST
def habit_complete_view(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    service = HabitService()
    service.complete_habit(habit, date.today())

    # Przeładuj widget
    return habit_list_widget(request)