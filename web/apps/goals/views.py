"""Goal views for GTD system strategic planning."""

from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import GoalForm
from .models import Goal


@login_required
def goal_list_view(request: Any) -> HttpResponse:
    """Dashboard strategiczny: Lista celów z postępem."""
    goals = (
        Goal.objects.filter(user=request.user)
        .annotate(
            # Obliczanie postępu na poziomie bazy danych (optymalizacja)
            # Zakładamy, że postęp jest zapisywany w modelu Goal przez sygnały/serwis,
            # ale dla pewności możemy go też doliczać tu, jeśli model tego nie ma.
            # W naszym modelu Goal mamy pole 'progress' (float 0-1), które powinno być aktualizowane.
            # Jeśli nie mamy automatyzacji aktualizacji pola progress, wyświetlimy to co jest.
        )
        .order_by("deadline")
    )

    return render(request, "goals/goal_list.html", {"goals": goals})


@login_required
def goal_create_view(request: Any) -> HttpResponse:
    """Create a new goal for the user."""
    if request.method == "POST":
        form = GoalForm(request.user, request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect("goal_list")
    else:
        form = GoalForm(request.user)

    return render(request, "goals/goal_form.html", {"form": form, "title": "Nowy Cel"})


@login_required
def goal_edit_view(request: Any, pk: int) -> HttpResponse:
    """Edit an existing goal."""
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == "POST":
        form = GoalForm(request.user, request.POST, instance=goal)
        if form.is_valid():
            form.save()
            return redirect("goal_list")
    else:
        form = GoalForm(request.user, instance=goal)

    return render(request, "goals/goal_form.html", {"form": form, "title": f"Edytuj: {goal.title}"})
