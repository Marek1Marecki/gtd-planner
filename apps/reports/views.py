from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from apps.tasks.models import Task
from apps.projects.models import Project
from apps.goals.models import Goal
from .domain.services import ReportService
from apps.tasks.domain.services.tickler import TicklerService
from django.utils import timezone
from datetime import date, timedelta
from apps.tasks.models import RecurringPattern
from .models import ReviewSession
from django import forms
from apps.areas.models import Area


# Prosty formularz (można w forms.py, ale tu szybciej dla MVP)
# Formularz inline (można przenieść do forms.py)
class ReviewForm(forms.ModelForm):
    class Meta:
        model = ReviewSession
        fields = ['reflection', 'next_week_priorities']
        widgets = {
            'reflection': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Co poszło dobrze? Co poprawić?'}),
            'next_week_priorities': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Główne cele na przyszły tydzień...'}),
        }


@login_required
def stats_api_view(request):
    """
    API zwracające dane do wykresów (Activity, Status, Areas).
    """
    service = ReportService()

    # 1. Pobierz podstawowe statystyki
    stats_data = service.get_weekly_stats(request.user)

    # 2. Pobierz dane o obszarach
    area_data = service.get_area_distribution(request.user)

    # 3. Pobierz skuteczność nawyków
    habit_data = service.get_habit_stats(request.user)

    # 4. NOWE: Pobierz zdrowie zadań cyklicznych
    recurring_data = service.get_recurring_health(request.user)

    # Zbuduj odpowiedź
    response_data = {
        'period': stats_data['period'],
        'completed': stats_data['completed'],
        'created': stats_data['created'],
        'velocity': stats_data['velocity'],
        'breakdown': stats_data['breakdown'],
        'area_chart': area_data,
        'habit_stats': habit_data,
        'recurring_stats': recurring_data
    }

    return JsonResponse(response_data)


@login_required
def weekly_review_view(request):
    user = request.user
    today = date.today()
    tickler = TicklerService()
    service = ReportService()

    # ----------------------------------------------------
    # 1. Obsługa Zapisu Sesji (Formularz)
    # ----------------------------------------------------
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = user
            session.save()
            return redirect('weekly_review')  # PRG pattern
    else:
        form = ReviewForm()

    last_review = ReviewSession.objects.filter(user=user).order_by('-date').first()

    # ----------------------------------------------------
    # 2. Tickler File & Stale Tasks
    # ----------------------------------------------------
    tasks_due_for_review = tickler.get_tasks_for_review(user)
    stale_tasks = tickler.get_stale_waiting_tasks(user)

    # ----------------------------------------------------
    # 3. Alerty Operacyjne (WIP, Recurring)
    # ----------------------------------------------------
    # WIP Limit
    active_tasks_count = Task.objects.filter(user=user, status__in=['scheduled', 'paused']).count()
    wip_limit = getattr(user.profile, 'wip_limit', 5)
    wip_alert = None
    if active_tasks_count > wip_limit:
        wip_alert = f"Masz {active_tasks_count} aktywnych zadań (Limit: {wip_limit})."

    # Broken Recurring Cycles
    broken_cycles = []
    active_patterns = RecurringPattern.objects.filter(user=user, is_active=True)
    for pat in active_patterns:
        if pat.next_run_date < today:
            has_active = Task.objects.filter(
                recurring_pattern=pat,
                status__in=['todo', 'scheduled', 'overdue']
            ).exists()
            if not has_active:
                broken_cycles.append(pat)

    # ----------------------------------------------------
    # 4. Alerty Strategiczne (Projekty, Cele, Obszary)
    # ----------------------------------------------------

    # Puste Projekty
    empty_projects = Project.objects.filter(user=user, status='active').annotate(
        total_tasks=Count('tasks')
    ).filter(total_tasks=0)

    # Cele bez postępu (Stagnant)
    # Deadline < 14 dni i Progress < 20%
    warning_date = today + timedelta(days=14)
    # Zakładamy, że pole progress istnieje w modelu Goal (dodane w poprzednim kroku)
    stagnant_goals = Goal.objects.filter(
        user=user,
        deadline__lte=warning_date,
        progress__lt=20
    )

    # Zaniedbane Obszary (Neglected Areas) - NOWE
    # Obszary, w których nie ukończono żadnego zadania w ostatnich 7 dniach
    week_ago = today - timedelta(days=7)
    neglected_areas = []
    all_areas = Area.objects.filter(user=user)  # Można dodać is_active=True

    for area in all_areas:
        completed_count = Task.objects.filter(
            area=area,
            status='done',
            updated_at__gte=week_ago
        ).count()

        if completed_count == 0:
            neglected_areas.append(area)

    context_data = service.get_context_distribution(request.user)

    return render(request, 'reports/weekly_review.html', {
        'review_form': form,
        'last_review': last_review,

        'due_review': tasks_due_for_review,
        'stale_tasks': stale_tasks,

        'wip_alert': wip_alert,
        'broken_cycles': broken_cycles,

        'empty_projects': empty_projects,
        'stagnant_goals': stagnant_goals,
        'neglected_areas': neglected_areas,
        'context_data': context_data
    })


@login_required
def reports_dashboard_view(request):
    """Główny widok Raportów (kontener dla wykresów)."""
    return render(request, 'reports/dashboard.html')
