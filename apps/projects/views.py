from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Project
from apps.tasks.models import Task  # Potrzebne do wyświetlenia zadań w projekcie


@login_required
def project_list_view(request):
    """Widok listy projektów (tylko główne, reszta w rekurencji)."""
    # Pobieramy tylko projekty 'root' (bez rodzica)
    root_projects = Project.objects.filter(
        user=request.user,
        parent_project__isnull=True
    ).prefetch_related('subprojects')  # Optymalizacja zapytań

    return render(request, 'projects/project_list.html', {
        'projects': root_projects
    })


@login_required
def project_detail_view(request, pk):
    """Dashboard konkretnego projektu."""
    project = get_object_or_404(Project, pk=pk, user=request.user)

    # Pobierz zadania tego projektu
    tasks = project.tasks.all().order_by('is_critical_path', '-priority')

    # Oblicz postęp (Prosty wariant, później użyjemy serwisu domenowego)
    total = tasks.count()
    completed = tasks.filter(status='done').count()
    progress = int((completed / total) * 100) if total > 0 else 0

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'tasks': tasks,
        'progress': progress
    })


@login_required
def project_create_view(request):
    """Prosty widok tworzenia projektu."""
    if request.method == 'POST':
        title = request.POST.get('title')
        parent_id = request.POST.get('parent_id')

        parent = None
        if parent_id:
            parent = Project.objects.get(id=parent_id)

        Project.objects.create(user=request.user, title=title, parent_project=parent)
        return redirect('project_list')

    # Do formularza potrzebujemy listy potencjalnych rodziców
    all_projects = Project.objects.filter(user=request.user)
    return render(request, 'projects/project_form.html', {'all_projects': all_projects})