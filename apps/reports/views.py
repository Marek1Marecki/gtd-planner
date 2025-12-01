from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.tasks.models import Task
from .domain.services import ReportService
from apps.tasks.domain.services.tickler import TicklerService


@login_required
def stats_api_view(request):
    service = ReportService()
    data = service.get_weekly_stats(request.user)
    return JsonResponse(data)


@login_required
def weekly_review_view(request):
    """Dashboard Przeglądu Tygodniowego."""

    tickler = TicklerService()

    # 1. Zadania, które "wyskoczyły" w kalendarzu
    tasks_due_for_review = tickler.get_tasks_for_review(request.user)

    # 2. "Zgniłe" oczekiwania (Alert)
    stale_tasks = tickler.get_stale_waiting_tasks(request.user)

    # 1. Pobierz zadania do przejrzenia (Tickler File)
    waiting_tasks = Task.objects.filter(user=request.user, status='waiting')
    delegated_tasks = Task.objects.filter(user=request.user, status='delegated')
    postponed_tasks = Task.objects.filter(user=request.user, status='postponed')

    # 2. Alerty (Zadania 'Paused' > 3 dni - uproszczona logika)
    from django.utils import timezone
    from datetime import timedelta
    three_days_ago = timezone.now() - timedelta(days=3)
    stale_paused = Task.objects.filter(user=request.user, status='paused', updated_at__lte=three_days_ago)

    return render(request, 'reports/weekly_review.html', {
        'due_review': tasks_due_for_review,
        'stale_tasks': stale_tasks,
        'waiting_tasks': waiting_tasks,
        'delegated_tasks': delegated_tasks,
        'postponed_tasks': postponed_tasks,
        'stale_paused': stale_paused
    })


@login_required
def reports_dashboard_view(request):
    """Główny widok Raportów (kontener dla wykresów)."""
    return render(request, 'reports/dashboard.html')
