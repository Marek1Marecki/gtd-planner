from datetime import date, datetime, timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Importy z innych aplikacji (Modularność!)
from apps.tasks.adapters.orm_repositories import DjangoTaskRepository
from .adapters.google_calendar import GoogleCalendarAdapter
from apps.calendar_app.domain.services import SchedulerService
from apps.core.models import UserProfile

@login_required
def daily_view(request):
    """
    Widok Kalendarza z logiką Dual Timeline (Służbowe vs Prywatne).
    """

    # 1. Kontekst Czasu
    today = date.today()
    now = datetime.now(timezone.utc)

    # Pobierz profil (dla godzin)
    try:
        profile = request.user.profile
    except:
        profile = UserProfile.objects.create(user=request.user)

    # 2. Pobierz Wszystkie Zadania
    task_repo = DjangoTaskRepository()
    all_tasks = task_repo.get_active_tasks()

    # 3. Podział na Domeny (Work vs Personal)
    work_tasks = [t for t in all_tasks if not t.is_private]
    personal_tasks = [t for t in all_tasks if t.is_private]

    # 4. Pobierz Fixed Events (Sztywne spotkania)
    # Pobieramy raz, użyjemy ich do blokowania obu osi czasu
    calendar_provider = GoogleCalendarAdapter()
    fixed_events = calendar_provider.get_events(request.user.id, today)

    scheduler = SchedulerService()

    # ==========================================
    # TIMELINE 1: PRACA (Work Window)
    # ==========================================
    work_windows = scheduler.calculate_free_windows(
        today,
        fixed_events,
        work_start=profile.work_start_hour,
        work_end=profile.work_end_hour
    )

    work_schedule = scheduler.schedule_tasks(
        work_tasks,
        work_windows,
        now,
        user_profile=profile
    )

    # ==========================================
    # TIMELINE 2: PRYWATNE (Personal Window)
    # ==========================================
    personal_windows = scheduler.calculate_free_windows(
        today,
        fixed_events,
        work_start=profile.personal_start_hour,
        work_end=profile.personal_end_hour
    )

    personal_schedule = scheduler.schedule_tasks(
        personal_tasks,
        personal_windows,
        now,
        user_profile=profile
    )

    # ==========================================
    # 5. Scalanie i Wyświetlanie
    # ==========================================

    timeline_items = []

    # Dodaj Fixed Events
    for event in fixed_events:
        duration_min = int((event.end_time - event.start_time).total_seconds() / 60)
        timeline_items.append({
            'title': event.title,
            'start': event.start_time,
            'end': event.end_time,
            'type': 'fixed',
            'duration': duration_min,
            'priority': None,
            'color': '#343a40'  # Ciemny szary
        })

    # Dodaj Zaplanowane (Work + Personal)
    full_schedule = work_schedule + personal_schedule
    scheduled_task_ids = set()

    for item in full_schedule:
        duration_min = int((item.end - item.start).total_seconds() / 60)
        # Kolor z obszaru (jeśli jest)
        task_color = item.task.area_color or ("#0d6efd" if not item.task.is_private else "#198754")

        timeline_items.append({
            'title': item.task.title,
            'start': item.start,
            'end': item.end,
            'type': 'dynamic',
            'duration': duration_min,
            'priority': item.task.priority,
            'color': task_color,
            'task_id': item.task.id  # Potrzebne do akcji HTMX
        })
        scheduled_task_ids.add(item.task.id)

    # Sortuj chronologicznie
    timeline_items.sort(key=lambda x: x['start'])

    # 6. Backlog (To co się nie zmieściło w ŻADNYM oknie)
    backlog_tasks = [t for t in all_tasks if t.id not in scheduled_task_ids]

    # --- PRZYWRÓCONA LOGIKA HTMX ---
    if request.headers.get('HX-Request'):
        base_template = 'base_htmx.html'
    else:
        base_template = 'base.html'

    return render(request, 'calendar/daily_view.html', {
        'timeline_items': timeline_items,
        'backlog_tasks': backlog_tasks,
        'today': today,
        'base_template': base_template
    })