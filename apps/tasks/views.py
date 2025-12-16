# apps/tasks/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .adapters.orm_repositories import DjangoTaskRepository
from .application.use_cases import CreateTaskUseCase, CreateTaskInput
from .models import Task
from apps.projects.models import Project
from apps.contexts.models import Context
from .filters import TaskFilter
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.tasks.domain.services import TaskService
from .domain.entities import TaskEntity, TaskStatus
from .models import ChecklistItem
from apps.areas.models import Area
from apps.goals.models import Goal
from apps.reports.models import ActivityLog
from django.contrib.contenttypes.models import ContentType


@login_required
def task_list_view(request):
    """Widok listy zadań."""
    # Pobieramy zadania zalogowanego użytkownika
    tasks = Task.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'tasks/task_list.html', {'tasks': tasks})


@login_required
def task_create_view(request):
    """Widok tworzenia zadania (korzysta z Clean Architecture)."""
    if request.method == "POST":
        title = request.POST.get('title')
        desc = request.POST.get('description')
        d_min = request.POST.get('duration_min')
        d_max = request.POST.get('duration_max')
        project_id = request.POST.get('project_id')
        energy = request.POST.get('energy_required')
        is_private = request.POST.get('is_private') == 'on'
        context_id = request.POST.get('context_id')
        area_id = request.POST.get('area_id')
        is_milestone = request.POST.get('is_milestone') == 'on'
        goal_id = request.POST.get('goal_id')

        # Konwersja project_id (pusty string -> None)
        project_id_int = int(project_id) if project_id else None

        # Konwersja na int lub None (bo string "" to nie None)
        ctx_id_val = int(context_id) if context_id else None

        # 1. Przygotowanie DTO (Data Transfer Object)
        input_dto = CreateTaskInput(
            title=title,
            user_id=request.user.id,
            description=desc,
            duration_min=int(d_min) if d_min else None,
            duration_max=int(d_max) if d_max else None,
            project_id=project_id_int,
            energy_required=int(energy) if energy else 2,
            is_private=is_private,
            context_id=ctx_id_val,
            area_id=int(area_id) if area_id else None,
            is_milestone=is_milestone,
            goal_id=int(goal_id) if goal_id else None
        )

        # 2. Złożenie Use Case (Manual Dependency Injection)
        repo = DjangoTaskRepository()
        use_case = CreateTaskUseCase(repository=repo)

        # 3. Wykonanie logiki biznesowej
        try:
            use_case.execute(input_dto)

            # Jeśli wybrano projekt, przekieruj do widoku projektu, w przeciwnym razie do listy zadań
            if project_id_int:
                return redirect('project_detail', pk=project_id_int)
            return redirect('task_list')

        except ValueError as e:
            return HttpResponse(f"Error: {e}", status=400)

    # GET: Wyświetl formularz
    # Pobieramy projekty użytkownika do listy rozwijanej
    projects = Project.objects.filter(user=request.user)
    contexts = Context.objects.filter(user=request.user, is_active=True)
    areas = Area.objects.filter(user=request.user)
    goals = Goal.objects.filter(user=request.user)

    return render(request, 'tasks/task_form.html', {
        'projects': projects,
        'contexts': contexts,
        'areas': areas,
        'goals': goals,
    })


@login_required
def task_search_view(request):
    # Pobieramy wszystkie zadania użytkownika
    # (Możemy tu dodać .select_related('context', 'project') dla optymalizacji)
    qs = Task.objects.filter(user=request.user).select_related('context', 'project').order_by('-created_at')

    f = TaskFilter(request.GET, queryset=qs)

    return render(request, 'tasks/task_search.html', {'filter': f})


@require_http_methods(["POST"])
@login_required
def task_complete_view(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    # Używamy serwisu (Clean Architecture)
    repo = DjangoTaskRepository()
    service = TaskService(repo)
    service.complete_task(task.id)

    # Zwracamy pusty string (usuwa element) lub zaktualizowany wiersz
    # Dla prostoty: zwróćmy fragment HTML z "Zrobione!"
    return HttpResponse('<span class="badge bg-success">Zrobione!</span>')


@require_http_methods(["POST"])
@login_required
def task_force_today_view(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    # Logika: Ustaw deadline na dziś, status na scheduled, priorytet na max
    task.due_date = timezone.now()
    task.status = 'scheduled'
    task.priority = 5  # Boost!
    task.save()

    return HttpResponse('<span class="badge bg-info">Przeniesiono na Dziś!</span>')


@require_http_methods(["POST"])
@login_required
def task_resume_view(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if task.status == 'paused':
        task.status = 'todo'  # Wracamy do puli
        # Opcjonalnie: task.percent_complete zostaje bez zmian (historia postępu)
        task.save()
        return HttpResponse('<span class="badge bg-warning text-dark">Wznowiono!</span>')

    return HttpResponse('Błąd', status=400)


@login_required
def task_edit_view(request, pk):
    # 1. Pobierz zadanie (zabezpieczenie, że należy do usera)
    task_model = get_object_or_404(Task, pk=pk, user=request.user)

    # Inicjalizacja repo
    repo = DjangoTaskRepository()

    if request.method == "POST":
        # 2. Pobierz dane z formularza
        title = request.POST.get('title')
        description = request.POST.get('description')
        d_min = request.POST.get('duration_min')
        d_max = request.POST.get('duration_max')
        project_id = request.POST.get('project_id')
        context_id = request.POST.get('context_id')
        energy = request.POST.get('energy_required')
        is_private = request.POST.get('is_private') == 'on'
        area_id = request.POST.get('area_id')
        is_milestone = request.POST.get('is_milestone') == 'on'
        goal_id = request.POST.get('goal_id')

        # 3. Zaktualizuj Encję (Tworzymy obiekt z ID, co wymusi UPDATE w repo)
        updated_task = TaskEntity(
            id=task_model.id,  # WAŻNE: Przekazujemy ID
            title=title,
            description=description,
            status=TaskStatus(task_model.status),  # Zachowujemy stary status
            duration_min=int(d_min) if d_min else None,
            duration_max=int(d_max) if d_max else None,
            project_id=int(project_id) if project_id else None,
            context_id=int(context_id) if context_id else None,
            energy_required=int(energy) if energy else 2,
            is_private=is_private,
            percent_complete=task_model.percent_complete,
            area_id=int(area_id) if area_id else None,
            is_milestone=is_milestone,
            goal_id=int(goal_id) if goal_id else None
        )

        # 4. Zapisz (Repozytorium wykryje ID i zrobi UPDATE)
        repo.save(updated_task)  # user_id nie jest potrzebne przy update

        return redirect('task_list')

    # GET: Pobierz dane do formularza
    projects = Project.objects.filter(user=request.user)
    contexts = Context.objects.filter(user=request.user, is_active=True)
    areas = Area.objects.filter(user=request.user)
    goals = Goal.objects.filter(user=request.user)

    return render(request, 'tasks/task_form.html', {
        'task': task_model,  # Przekazujemy obiekt do wstępnego wypełnienia
        'projects': projects,
        'contexts': contexts,
        'areas': areas,
        'goals': goals,
    })


@require_http_methods(["POST"])
@login_required
def checklist_add_view(request, task_id):
    task = get_object_or_404(Task, pk=task_id, user=request.user)
    text = request.POST.get('text')

    if text:
        ChecklistItem.objects.create(task=task, text=text)

    # Obliczenie postępu
    total = task.checklist_items.count()
    done = task.checklist_items.filter(is_completed=True).count()
    progress = int((done / total) * 100) if total > 0 else 0

    return render(request, 'tasks/partials/checklist.html', {
        'task': task,
        'progress': progress
    })


@require_http_methods(["POST"])
@login_required
def checklist_toggle_view(request, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id, task__user=request.user)
    item.is_completed = not item.is_completed
    item.save()

    task = item.task

    # Obliczenie postępu
    total = task.checklist_items.count()
    done = task.checklist_items.filter(is_completed=True).count()
    progress = int((done / total) * 100) if total > 0 else 0

    return render(request, 'tasks/partials/checklist.html', {
        'task': task,
        'progress': progress
    })


@require_http_methods(["DELETE"])
@login_required
def checklist_delete_view(request, item_id):
    item = get_object_or_404(ChecklistItem, pk=item_id, task__user=request.user)
    task = item.task
    item.delete()

    # Obliczenie postępu
    total = task.checklist_items.count()
    done = task.checklist_items.filter(is_completed=True).count()
    progress = int((done / total) * 100) if total > 0 else 0

    return render(request, 'tasks/partials/checklist.html', {
        'task': task,
        'progress': progress
    })


@login_required
def task_detail_hx_view(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    # Pobierz historię aktywności dla tego zadania
    # Używamy ContentType, aby znaleźć logi powiązane z modelem Task
    ct = ContentType.objects.get_for_model(Task)
    activities = ActivityLog.objects.filter(
        content_type=ct,
        object_id=task.id
    ).order_by('-timestamp')

    return render(request, 'tasks/partials/task_detail_sidebar.html', {
        'task': task,
        'activities': activities  # <-- Przekazujemy logi
    })


@require_http_methods(["POST"])
@login_required
def task_tiny_step_view(request, pk):
    """Tworzy 5-minutowe zadanie wstępne i blokuje oryginał."""
    original_task = get_object_or_404(Task, pk=pk, user=request.user)

    # Tworzymy Tiny Step
    tiny_task = Task.objects.create(
        user=request.user,
        title=f"START: {original_task.title}",
        description=f"5-minutowa rozgrzewka dla zadania: {original_task.title}",
        project=original_task.project,
        area=original_task.area,
        context=original_task.context,
        duration_min=5,
        duration_max=5,
        priority=original_task.priority,
        status='todo'
    )

    # Blokujemy oryginał
    original_task.status = 'blocked'
    original_task.blocked_by.add(tiny_task)
    original_task.save()

    return HttpResponse(f'<span class="badge bg-success">Utworzono: {tiny_task.title}</span>')


@require_http_methods(["POST"])
@login_required
def task_split_view(request, pk):
    """Zamyka obecne zadanie i tworzy nowe na pozostały czas."""
    original = get_object_or_404(Task, pk=pk, user=request.user)

    try:
        remaining_mins = int(request.POST.get('remaining_minutes'))
    except (TypeError, ValueError):
        return HttpResponse("Błędny czas", status=400)

    if remaining_mins <= 0:
        return HttpResponse("Czas musi być dodatni", status=400)

    # 1. Zamknij oryginał
    original.status = 'done'
    original.save()

    # 2. Utwórz nowe zadanie (Resztę)
    new_task = Task.objects.create(
        user=request.user,
        title=f"[Dokończenie] {original.title}",
        description=original.description,  # Kopiujemy opis
        project=original.project,
        area=original.area,
        context=original.context,
        priority=original.priority,  # Zachowujemy wysoki priorytet
        energy_required=original.energy_required,
        is_private=original.is_private,

        # Nowy czas
        duration_min=remaining_mins,
        duration_max=remaining_mins,

        status='todo'  # Trafi do Schedulera
    )

    # Odświeżamy widok (zwracamy np. sukces lub przeładowujemy)
    return HttpResponse(f'<span class="badge bg-warning text-dark">Przełożono {remaining_mins} min</span>')
