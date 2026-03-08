"""Report views for GTD system analytics and weekly reviews."""

from datetime import date, timedelta
from typing import Any

from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from apps.areas.models import Area
from apps.goals.models import Goal
from apps.notes.models import Note
from apps.projects.models import Project
from apps.tasks.application.tickler import TicklerService
from apps.tasks.models import RecurringPattern, Task

from .domain.services import ReportService
from .models import ReviewSession


# Prosty formularz (można w forms.py, ale tu szybciej dla MVP)
# Formularz inline (można przenieść do forms.py)
class ReviewForm(forms.ModelForm):  # type: ignore
    """Form for creating weekly review sessions."""

    class Meta:
        """Meta options for ReviewForm."""

        model = ReviewSession
        fields = ["reflection", "next_week_priorities"]
        widgets = {
            "reflection": forms.Textarea(
                attrs={"rows": 3, "class": "form-control", "placeholder": "Co poszło dobrze? Co poprawić?"}
            ),
            "next_week_priorities": forms.Textarea(
                attrs={"rows": 3, "class": "form-control", "placeholder": "Główne cele na przyszły tydzień..."}
            ),
        }


@login_required
def stats_api_view(request: Any) -> JsonResponse:
    """API endpoint returning data for charts (Activity, Status, Areas)."""
    service = ReportService()

    # 1. Pobierz podstawowe statystyki
    stats_data = service.get_weekly_stats(request.user)

    # 2. Pobierz dane o obszarach
    area_data = service.get_area_distribution(request.user)

    # 3. Pobierz skuteczność nawyków
    habit_data = service.get_habit_stats(request.user)

    # 4. NOWE: Pobierz zdrowie zadań cyklicznych
    recurring_data = service.get_recurring_health(request.user)

    # 5. NOWE: Pobierz dane o postępach celów
    goal_progress_data = service.get_goal_progress(request.user)

    # 6. NOWE: Pobierz statystyki notatek
    note_count_data = service.get_note_stats(request.user)

    # 7. NOWE: Pobierz statusy projektów
    project_status_data = service.get_project_status(request.user)

    # Zbuduj odpowiedź
    response_data = {
        "weekly_stats": stats_data,  # Add the weekly_stats key
        "period": stats_data["period"],
        "completed": stats_data["completed"],
        "created": stats_data["created"],
        "velocity": stats_data["velocity"],
        "breakdown": stats_data["breakdown"],
        "area_distribution": area_data,  # Match test expectation
        "habit_completion": habit_data,  # Match test expectation
        "recurring_tasks": recurring_data,  # Match test expectation
        "goal_progress": goal_progress_data,
        "note_count": note_count_data,
        "project_status": project_status_data,
    }

    return JsonResponse(response_data)


@login_required
def weekly_review_view(request: Any) -> HttpResponse:
    """Display weekly review dashboard with GTD methodology insights."""
    user = request.user
    today = date.today()
    tickler = TicklerService()
    service = ReportService()

    # ----------------------------------------------------
    # 1. Obsługa Zapisu Sesji (Formularz)
    # ----------------------------------------------------
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = user
            session.save()
            return redirect("weekly_review")  # PRG pattern
    else:
        form = ReviewForm()

    last_review = ReviewSession.objects.filter(user=user).order_by("-date").first()
    recent_reviews = ReviewSession.objects.filter(user=user).order_by("-date")[:5]

    # ----------------------------------------------------
    # 2. Tickler File & Stale Tasks
    # ----------------------------------------------------
    tasks_due_for_review = tickler.get_tasks_for_review(user)
    stale_tasks = tickler.get_stale_waiting_tasks(user)

    # ----------------------------------------------------
    # 3. Alerty Operacyjne (WIP, Recurring)
    # ----------------------------------------------------
    # WIP Limit
    active_tasks_count = Task.objects.filter(user=user, status__in=["scheduled", "paused"]).count()
    wip_limit = getattr(user.profile, "wip_limit", 5)
    wip_alert = None
    if active_tasks_count > wip_limit:
        wip_alert = f"Masz {active_tasks_count} aktywnych zadań (Limit: {wip_limit})."

    # Broken Recurring Cycles
    broken_cycles = []
    active_patterns = RecurringPattern.objects.filter(user=user, is_active=True)
    for pat in active_patterns:
        if pat.next_run_date < today:
            has_active = Task.objects.filter(
                recurring_pattern=pat, status__in=["todo", "scheduled", "overdue"]
            ).exists()
            if not has_active:
                broken_cycles.append(pat)

    # ----------------------------------------------------
    # 4. Alerty Strategiczne (Projekty, Cele, Obszary)
    # ----------------------------------------------------

    # Puste Projekty
    empty_projects = (
        Project.objects.filter(user=user, status="active").annotate(total_tasks=Count("tasks")).filter(total_tasks=0)
    )

    # Cele bez postępu (Stagnant)
    # Deadline < 14 dni i Progress < 20%
    warning_date = today + timedelta(days=14)
    # Zakładamy, że pole progress istnieje w modelu Goal (dodane w poprzednim kroku)
    stagnant_goals = Goal.objects.filter(user=user, deadline__lte=warning_date, progress__lt=20)

    # Zaniedbane Obszary (Neglected Areas) - NOWE
    # Obszary, w których nie ukończono żadnego zadania w ostatnich 7 dniach
    week_ago = today - timedelta(days=7)
    neglected_areas = []
    all_areas = Area.objects.filter(user=user)  # Można dodać is_active=True

    for area in all_areas:
        completed_count = Task.objects.filter(area=area, status="done", updated_at__gte=week_ago).count()

        if completed_count == 0:
            neglected_areas.append(area)

    # 5. Łańcuchy Blokad (Dependency Chains)
    service = ReportService()  # Jeśli nie masz instancji
    blocking_chains = service.get_blocking_chains(user)

    context_data = service.get_context_distribution(request.user)

    # 6. Projekty Wstrzymane (On Hold)
    projects_on_hold = Project.objects.filter(user=user, status="on_hold")
    delegated_tasks = Task.objects.filter(user=user, status="delegated")
    postponed_tasks = Task.objects.filter(user=user, status="postponed")
    waiting_tasks = Task.objects.filter(user=user, status="waiting")

    # 6. Luźne Notatki (Inbox Notatek)
    # Notatki bez projektu i bez zadania
    loose_notes = Note.objects.filter(user=user, project__isnull=True, task__isnull=True).order_by("-created_at")

    # 7. Wszystkie zadania użytkownika (dla testu)
    all_tasks = Task.objects.filter(user=user)
    total_tasks = all_tasks.count()
    completed_tasks = all_tasks.filter(status="done").count()
    todo_tasks = all_tasks.filter(status="todo").count()
    scheduled_tasks = all_tasks.filter(status="scheduled").count()

    return render(
        request,
        "reports/weekly_review.html",
        {
            "tasks": all_tasks,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "todo_tasks": todo_tasks,
            "scheduled_tasks": scheduled_tasks,
            "review_form": form,
            "last_review": last_review,
            "recent_reviews": recent_reviews,
            "due_review": tasks_due_for_review,
            "stale_tasks": stale_tasks,
            "wip_alert": wip_alert,
            "broken_cycles": broken_cycles,
            "empty_projects": empty_projects,
            "stagnant_goals": stagnant_goals,
            "neglected_areas": neglected_areas,
            "context_data": context_data,
            "blocking_chains": blocking_chains,
            "delegated_tasks": delegated_tasks,
            "postponed_tasks": postponed_tasks,
            "waiting_tasks": waiting_tasks,
            "projects_on_hold": projects_on_hold,
            "loose_notes": loose_notes,
        },
    )


@login_required
def reports_dashboard_view(request: Any) -> HttpResponse:
    """Główny widok Raportów (kontener dla wykresów)."""
    return render(request, "reports/dashboard.html")
