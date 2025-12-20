# apps/calendar_app/views.py
from datetime import date, datetime, timezone, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Importy z innych aplikacji (Modularność!)
from apps.tasks.adapters.orm_repositories import DjangoTaskRepository
from .adapters.google_calendar import GoogleCalendarAdapter
from apps.calendar_app.domain.services import SchedulerService
from apps.core.models import UserProfile
from apps.tasks.models import Task


@login_required
def daily_view(request):
    """
    Widok Kalendarza z logiką Dual Timeline (Służbowe vs Prywatne).
    """

    # 1. Kontekst Czasu
    today = date.today()
    now = datetime.now(timezone.utc)

    # --- NOWE: Lazy Overdue Check (Sprzątanie przed planowaniem) ---
    # Znajdź zadania, które są aktywne, ale ich termin minął (wczoraj lub dawniej)
    # due_date jest typu Date (bez godziny) lub DateTime.
    # Zakładamy DateField lub porównujemy date().

    # Pobieramy kandydatów do przeterminowania
    overdue_candidates = Task.objects.filter(
        user=request.user,
        status__in=['todo', 'scheduled'],
        due_date__lt=today  # Ściśle mniejsze niż dzisiaj
    )

    if overdue_candidates.exists():
        count = overdue_candidates.update(status='overdue')
        print(f"Lazy Check: Zmieniono {count} zadań na OVERDUE.")

    # 2. Pobierz Zadania (Teraz pobierze już bez tych overdue!)
    task_repo = DjangoTaskRepository()
    all_tasks = task_repo.get_active_tasks()  # Ta metoda filtruje tylko TODO/SCHEDULED

    # Dodatkowo pobierzemy listę overdue, żeby wyświetlić w sekcji alarmowej
    overdue_tasks = Task.objects.filter(user=request.user, status='overdue')

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
        'overdue_tasks': overdue_tasks,
        'today': today,
        'base_template': base_template
    })


@login_required
def weekly_view(request):
    """Widok Tygodnia (Pon-Ndz)."""

    # 1. Ustal poniedziałek bieżącego tygodnia
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday

    # 2. Uruchom logikę planowania
    scheduler = SchedulerService()
    week_plan = scheduler.get_weekly_plan(request.user, start_of_week)

    # 3. Renderuj
    # Jeśli HTMX, zwróć tylko tabelę
    template_name = 'calendar/weekly_view.html'
    if request.headers.get('HX-Request'):
        base_template = 'base_htmx.html'
    else:
        base_template = 'base.html'

    return render(request, template_name, {
        'week_plan': week_plan,
        'start_date': start_of_week,
        'end_date': start_of_week + timedelta(days=6),
        'base_template': base_template
    })
