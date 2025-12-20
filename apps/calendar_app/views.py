# apps/calendar_app/views.py
import calendar
from datetime import date, datetime, timezone, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Importy z innych aplikacji (Modularność!)
from apps.tasks.adapters.orm_repositories import DjangoTaskRepository
from .adapters.google_calendar import GoogleCalendarAdapter
from apps.calendar_app.domain.services import SchedulerService
from apps.core.models import UserProfile
from apps.tasks.models import Task
from apps.goals.models import Goal
from apps.projects.models import Project


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

    # 1. Ustal bazową datę dla tygodnia
    # Jeśli są parametry w URL, użyj ich do ustalenia daty
    try:
        year = int(request.GET.get('year'))
        month = int(request.GET.get('month'))
        day_of_month = int(request.GET.get('day'))
        base_date = date(year, month, day_of_month)
    except (TypeError, ValueError):
        base_date = date.today()

    # Ustal poniedziałek tygodnia, do którego należy base_date
    start_of_week = base_date - timedelta(days=base_date.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)

    # 2. Uruchom logikę planowania
    scheduler = SchedulerService()
    week_plan = scheduler.get_weekly_plan(request.user, start_of_week)

    # 3. Generuj linki nawigacyjne
    prev_week_start = start_of_week - timedelta(weeks=1)
    next_week_start = start_of_week + timedelta(weeks=1)

    # Przygotuj parametry URL
    prev_week_params = f"?year={prev_week_start.year}&month={prev_week_start.month}&day={prev_week_start.day}"
    next_week_params = f"?year={next_week_start.year}&month={next_week_start.month}&day={next_week_start.day}"

    # ... (logika base_template HTMX) ...
    template_name = 'calendar/weekly_view.html'
    if request.headers.get('HX-Request'):
        base_template = 'base_htmx.html'
    else:
        base_template = 'base.html'

    return render(request, template_name, {
        'week_plan': week_plan,
        'start_date': start_of_week,
        'end_date': end_of_week,
        'today': date.today(),  # Dodaj, żeby wyróżniać dzisiejszą kolumnę
        'prev_week_params': prev_week_params,
        'next_week_params': next_week_params,
        'base_template': base_template
    })


@login_required
def monthly_view(request):
    """Widok Strategiczny Miesiąca."""

    # 1. Ustal rok i miesiąc (domyślnie obecny)
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # 2. Pobierz dane strategiczne
    # Cele
    goals = Goal.objects.filter(
        user=request.user, deadline__year=year, deadline__month=month
    )
    # Projekty
    projects = Project.objects.filter(
        user=request.user, deadline__year=year, deadline__month=month
    )
    # Kamienie Milowe (Zadania oznaczone jako milestone)
    milestones = Task.objects.filter(
        user=request.user,
        due_date__year=year, due_date__month=month,
        is_milestone=True
    )

    # 3. Zmapuj dane na dni miesiąca: { 15: [obj1, obj2], 20: [obj3] }
    events_by_day = {}

    def add_event(day, obj, type, color):
        if day not in events_by_day: events_by_day[day] = []
        events_by_day[day].append({'title': str(obj), 'type': type, 'color': color})

    for g in goals: add_event(g.deadline.day, g, 'Cel', 'bg-danger')
    for p in projects: add_event(p.deadline.day, p, 'Projekt', 'bg-primary')
    for m in milestones: add_event(m.due_date.day, m, 'Milestone', 'bg-info')

    # 4. Generuj kalendarz (Macierz: [[0,0,1,2,3...], [4,5...]])
    cal = calendar.monthcalendar(year, month)

    # Nawigacja (Poprzedni/Następny)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    # Jeśli HTMX...
    if request.headers.get('HX-Request'):
        base_template = 'base_htmx.html'
    else:
        base_template = 'base.html'

    return render(request, 'calendar/monthly_view.html', {
        'calendar': cal,  # Macierz dni
        'events_by_day': events_by_day,
        'current_date': date(year, month, 1),
        'prev_date': f"?year={prev_year}&month={prev_month}",
        'next_date': f"?year={next_year}&month={next_month}",
        'base_template': base_template
    })
