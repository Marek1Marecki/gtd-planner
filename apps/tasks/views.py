# apps/tasks/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .adapters.orm_repositories import DjangoTaskRepository
from .application.use_cases import CreateTaskUseCase, CreateTaskInput
from .models import Task  # Import modelu do prostego odczytu listy
from apps.projects.models import Project


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

        # Konwersja project_id (pusty string -> None)
        project_id_int = int(project_id) if project_id else None

        # 1. Przygotowanie DTO (Data Transfer Object)
        input_dto = CreateTaskInput(
            title=title,
            user_id=request.user.id,
            description=desc,
            duration_min=int(d_min) if d_min else None,
            duration_max=int(d_max) if d_max else None,
            project_id=project_id_int,
            energy_required=int(energy) if energy else 2,
            is_private=is_private
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
    projects = Project.objects.filter(user=request.user).order_by('title')

    return render(request, 'tasks/task_form.html', {
        'projects': projects
    })