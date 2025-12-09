from django.http import JsonResponse
from django.shortcuts import render
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


# Prosty formularz (można w forms.py, ale tu szybciej dla MVP)
class ReviewForm(forms.ModelForm):
    class Meta:
        model = ReviewSession
        fields = ['reflection', 'next_week_priorities']
        widgets = {
            'reflection': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'next_week_priorities': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
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
    """Dashboard Przeglądu Tygodniowego."""

    tickler = TicklerService()
    user = request.user
    today = date.today()

    # --- 1. Obsługa Planowania Strategicznego ---
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = user
            session.save()
            # Można dodać redirect, żeby wyczyścić POST
    else:
        form = ReviewForm()

    # Pobierz ostatni plan (żeby wyświetlić "Aktualny Fokus")
    last_review = ReviewSession.objects.filter(user=user).order_by('-date').first()

    # --- 2. Alerty Recurring (Przerwane cykle) ---
    today = date.today()
    broken_cycles = []
    active_patterns = RecurringPattern.objects.filter(user=user, is_active=True)

    for pat in active_patterns:
        # Jeśli data następnego wykonania minęła...
        if pat.next_run_date < today:
            # ...i nie ma aktywnego zadania z tego szablonu
            has_active = Task.objects.filter(
                recurring_pattern=pat,
                status__in=['todo', 'scheduled', 'overdue']
            ).exists()
            if not has_active:
                broken_cycles.append(pat)

    # 1. Zadania, które "wyskoczyły" w kalendarzu
    tasks_due_for_review = tickler.get_tasks_for_review(request.user)
    # 2. "Zgniłe" oczekiwania (Alert)
    stale_tasks = tickler.get_stale_waiting_tasks(request.user)

    # 3. WIP Alert (Work In Progress)
    # Liczymy zadania zaplanowane na dziś (scheduled) oraz wstrzymane (paused) - czyli te "na stole"
    active_tasks_count = Task.objects.filter(
        user=request.user,
        status__in=['scheduled', 'paused']
    ).count()

    wip_limit = request.user.profile.wip_limit
    wip_alert = None

    if active_tasks_count > wip_limit:
        wip_alert = f"Masz {active_tasks_count} aktywnych zadań (Limit: {wip_limit}). Dokończ coś zanim zaczniesz nowe!"

    # A. Puste Projekty (Zombie Projects)
    # Projekty aktywne, które nie mają żadnych zadań (ani zakończonych, ani w toku)
    empty_projects = Project.objects.filter(user=user, status='active').annotate(
        total_tasks=Count('tasks')
    ).filter(total_tasks=0)

    # B. Cele bez postępu (Stagnant Goals)
    # Cele aktywne, deadline < 14 dni, postęp < 20% (lub 0.2)
    # Uwaga: Zakładam, że pole 'progress' w Goal jest float 0-100.
    warning_date = today + timedelta(days=14)
    stagnant_goals = Goal.objects.filter(
        user=user,
        # status='active', # Jeśli masz pole status w Goal
        deadline__lte=warning_date,
        progress__lt=20  # < 20%
    )

    # 1. Pobierz zadania do przejrzenia (Tickler File)
    waiting_tasks = Task.objects.filter(user=request.user, status='waiting')
    delegated_tasks = Task.objects.filter(user=request.user, status='delegated')
    postponed_tasks = Task.objects.filter(user=request.user, status='postponed')

    # 2. Alerty (Zadania 'Paused' > 3 dni - uproszczona logika)
    three_days_ago = timezone.now() - timedelta(days=3)
    stale_paused = Task.objects.filter(user=request.user, status='paused', updated_at__lte=three_days_ago)


    return render(request, 'reports/weekly_review.html', {
        'due_review': tasks_due_for_review,
        'stale_tasks': stale_tasks,
        'waiting_tasks': waiting_tasks,
        'delegated_tasks': delegated_tasks,
        'postponed_tasks': postponed_tasks,
        'stale_paused': stale_paused,
        'wip_alert': wip_alert,
        'empty_projects': empty_projects,
        'stagnant_goals': stagnant_goals,
        'broken_cycles': broken_cycles,
        'review_form': form,
        'last_review': last_review,
    })


@login_required
def reports_dashboard_view(request):
    """Główny widok Raportów (kontener dla wykresów)."""
    return render(request, 'reports/dashboard.html')
