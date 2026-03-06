"""Note views for GTD system note management."""

from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.models import Project  # Do selecta w formularzu

from .models import Note


@login_required
def note_list_view(request: Any) -> HttpResponse:
    """Display list of user's notes ordered by update time."""
    notes = Note.objects.filter(user=request.user).order_by("-updated_at")
    return render(request, "notes/note_list.html", {"notes": notes})


@login_required
def note_detail_view(request: Any, pk: int) -> HttpResponse:
    """Display detailed view of a specific note."""
    note = get_object_or_404(Note, pk=pk, user=request.user)
    return render(request, "notes/note_detail.html", {"note": note})


@login_required
def note_create_view(request: Any) -> HttpResponse:
    """Create a new note with optional project association."""
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        project_id = request.POST.get("project_id")

        # Prosta walidacja
        if title:
            project = None
            if project_id:
                project = Project.objects.get(id=project_id)

            Note.objects.create(user=request.user, title=title, content=content, project=project)
            return redirect("note_list")

    # Pobierz projekty do formularza
    projects = Project.objects.filter(user=request.user)
    return render(request, "notes/note_form.html", {"projects": projects})
