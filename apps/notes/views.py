from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Note
from apps.projects.models import Project  # Do selecta w formularzu


@login_required
def note_list_view(request):
    notes = Note.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'notes/note_list.html', {'notes': notes})


@login_required
def note_detail_view(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    return render(request, 'notes/note_detail.html', {'note': note})


@login_required
def note_create_view(request):
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        project_id = request.POST.get('project_id')

        # Prosta walidacja
        if title:
            project = None
            if project_id:
                project = Project.objects.get(id=project_id)

            Note.objects.create(
                user=request.user,
                title=title,
                content=content,
                project=project
            )
            return redirect('note_list')

    # Pobierz projekty do formularza
    projects = Project.objects.filter(user=request.user)
    return render(request, 'notes/note_form.html', {'projects': projects})