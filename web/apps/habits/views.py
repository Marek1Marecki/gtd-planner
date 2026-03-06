"""Habit views for GTD system daily tracking."""

from datetime import date
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Habit
from .services import HabitService


@login_required
def habit_list_widget(request: Any) -> HttpResponse:
    """Zwraca widget z listą nawyków na dziś."""
    habits = Habit.objects.filter(user=request.user, is_active=True)
    today = date.today()

    # for h in habits:
    #     # Check if habit was completed today by comparing last_completed_date
    #     h.is_completed_today = h.last_completed_date == today

    return render(
        request,
        "habits/partials/widget.html",
        {
            "habits": habits,
            "today": today,
        },
    )


@login_required
@require_POST
def habit_complete_view(request: Any, pk: int) -> HttpResponse:
    """Mark a habit as completed for today."""
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    service = HabitService()
    service.complete_habit(habit, date.today())

    # Przeładuj widget
    return habit_list_widget(request)
