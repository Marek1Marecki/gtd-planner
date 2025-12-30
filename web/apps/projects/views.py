from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Project
from .domain.prediction import ProjectPredictor
from apps.areas.models import Area
from apps.contexts.models import Tag


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

    # --- NOWE: Pobierz notatki ---
    # Używamy related_name='notes' zdefiniowanego w modelu Note
    notes = project.notes.all().order_by('-updated_at')

    # --- NOWE: Predykcja ---
    active_tasks = project.tasks.filter(status__in=['todo', 'scheduled', 'blocked'])

    # Pobierz capacity z profilu (jeśli mamy takie pole, lub użyj stałej)
    # user_capacity = request.user.profile.daily_project_hours * 60
    predictor = ProjectPredictor(daily_capacity_minutes=4 * 60)

    projected_date = predictor.predict_completion_date(active_tasks)

    # Sprawdź ryzyko
    risk_alert = False
    if project.deadline and projected_date > project.deadline:
        risk_alert = True

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'tasks': tasks,
        'progress': progress,
        'notes': notes,
        # Nowe dane:
        'projected_date': projected_date,
        'risk_alert': risk_alert
    })


@login_required
def project_create_view(request):
    """Prosty widok tworzenia projektu."""
    if request.method == 'POST':
        title = request.POST.get('title')
        parent_id = request.POST.get('parent_id')
        area_id = request.POST.get('area_id')
        tag_ids = request.POST.getlist('tags')  # <-- NOWE

        parent = None
        if parent_id:
            try:
                parent = Project.objects.get(id=parent_id)
            except Project.DoesNotExist:
                pass

        area = None
        if area_id:
            try:
                area = Area.objects.get(id=area_id)
            except Area.DoesNotExist:
                pass

        # Tworzymy projekt
        project = Project.objects.create(
            user=request.user,
            title=title,
            parent_project=parent,
            area=area
        )

        # Przypisujemy tagi (M2M wymaga istniejącego obiektu, dlatego robimy to po create)
        if tag_ids:
            project.tags.set(tag_ids)

        return redirect('project_list')

    # GET: Pobierz dane do formularzy
    all_projects = Project.objects.filter(user=request.user)
    areas = Area.objects.filter(user=request.user)
    all_tags = Tag.objects.filter(user=request.user)  # <-- NOWE

    return render(request, 'projects/project_form.html', {
        'all_projects': all_projects,
        'areas': areas,
        'all_tags': all_tags
    })