# apps/tasks/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .adapters.orm_repositories import DjangoTaskRepository
from .application.use_cases import CreateTaskUseCase, CreateTaskInput
from .models import Task  # Import modelu do prostego odczytu listy


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

        # 1. Przygotowanie DTO (Data Transfer Object)
        input_dto = CreateTaskInput(
            title=title,
            user_id=request.user.id,
            description=desc,
            duration_min=int(d_min) if d_min else None
        )

        # 2. Złożenie Use Case (Manual Dependency Injection)
        repo = DjangoTaskRepository()
        use_case = CreateTaskUseCase(repository=repo)

        # 3. Wykonanie logiki biznesowej
        try:
            use_case.execute(input_dto)
            return redirect('task_list')
        except ValueError as e:
            return HttpResponse(f"Error: {e}", status=400)

    return render(request, 'tasks/task_form.html')