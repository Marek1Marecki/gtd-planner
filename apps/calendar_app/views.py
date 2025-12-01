from datetime import date, datetime, timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Importy z innych aplikacji (Modularność!)
from apps.tasks.adapters.orm_repositories import DjangoTaskRepository
from .adapters.google_calendar import GoogleCalendarAdapter
from apps.calendar_app.domain.services import SchedulerService


@login_required
def daily_view(request):
    """
    Główny widok Kalendarza Dziennego.
    Orkiestruje pobieranie danych i uruchamianie algorytmu harmonogramowania.
    """

    # 1. Dane wejściowe (Kontekst czasu)
    today = date.today()
    # Używamy UTC dla spójności, w produkcji warto użyć user.timezone
    now = datetime.now(timezone.utc)

    # 2. Pobierz Zadania Elastyczne (Todo/Scheduled)
    # Korzystamy z Repozytorium zadań, aby pobrać encje domenowe
    task_repo = DjangoTaskRepository()
    tasks = task_repo.get_active_tasks()

    # 3. Pobierz Zadania Sztywne (Fixed Events) z Kalendarza
    # Na razie Mock, docelowo Google Calendar API
    calendar_provider = GoogleCalendarAdapter()
    fixed_events = calendar_provider.get_events(request.user.id, today)

    # 4. Uruchom Scheduler
    # Pobierz profil
    try:
        profile = request.user.profile
    except:
        # Fallback (powinien być obsłużony w signals, ale dla bezpieczeństwa)
        from apps.core.models import UserProfile
        profile = UserProfile.objects.create(user=request.user)

    scheduler = SchedulerService()

    # Krok A: Wyznacz okna (używając godzin z profilu)
    windows = scheduler.calculate_free_windows(
        today,
        fixed_events,
        work_start=profile.work_start_hour,  # <-- Z BAZY
        work_end=profile.work_end_hour  # <-- Z BAZY
    )

    # Krok B: Alokacja (przekazujemy cały profil dla energii)
    schedule = scheduler.schedule_tasks(
        tasks,
        windows,
        now,
        user_profile=profile  # <-- Z BAZY
    )

    # 5. Przygotuj dane do wyświetlenia (Timeline Items)
    # Łączymy "Fixed" i "Dynamic" w jedną listę, aby wyświetlić je chronologicznie
    timeline_items = []

    # Dodaj Fixed Events (Sztywne)
    for event in fixed_events:
        duration_min = int((event.end_time - event.start_time).total_seconds() / 60)
        timeline_items.append({
            'title': event.title,
            'start': event.start_time,
            'end': event.end_time,
            'type': 'fixed',
            'duration': duration_min,
            'priority': None,  # Fixed nie ma priorytetu w sensie GTD
        })

    # Dodaj Dynamic Tasks (Zaplanowane przez algorytm)
    scheduled_task_ids = set()
    for item in schedule:
        duration_min = int((item.end - item.start).total_seconds() / 60)
        timeline_items.append({
            'title': item.task.title,
            'start': item.start,
            'end': item.end,
            'type': 'dynamic',
            'duration': duration_min,
            'priority': item.task.priority,
        })
        scheduled_task_ids.add(item.task.id)

    # Sortuj wszystko chronologicznie po czasie startu
    timeline_items.sort(key=lambda x: x['start'])

    # 6. Oblicz Backlog (Zadania, które się nie zmieściły)
    backlog_tasks = [t for t in tasks if t.id not in scheduled_task_ids]

    # Wybierz szablon bazowy
    if request.headers.get('HX-Request'):
        base_template = 'base_htmx.html'
    else:
        base_template = 'base.html'

    return render(request, 'calendar/daily_view.html', {
        'timeline_items': timeline_items,
        'backlog_tasks': backlog_tasks,
        'today': today,
        'base_template': base_template  # Przekazujemy nazwę szablonu do extends
    })