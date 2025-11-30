from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.tasks.models import Task


@login_required
def weekly_review_view(request):
    """Dashboard Przeglądu Tygodniowego."""

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
        'waiting_tasks': waiting_tasks,
        'delegated_tasks': delegated_tasks,
        'postponed_tasks': postponed_tasks,
        'stale_paused': stale_paused
    })