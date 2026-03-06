"""Core views for GTD system dashboard and user management."""

# apps/core/views.py

import os
from datetime import date
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from google_auth_oauthlib.flow import Flow

from apps.tasks.models import Task

from .forms import UserProfileForm
from .models import GoogleCredentials, UserProfile

# Ścieżka do pliku JSON
CLIENT_SECRETS_FILE = os.path.join(settings.BASE_DIR, "client_secret.json")

# Sprawdzamy czy plik istnieje, jeśli nie - używamy mock
if not os.path.exists(CLIENT_SECRETS_FILE):
    # Dla testów - tworzymy mock secrets
    import json
    import tempfile

    mock_secrets = {
        "web": {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://127.0.0.1:8000/google/callback/"],
        }
    }

    # Tworzymy tymczasowy plik w katalogu tmp/
    tmp_dir = tempfile.gettempdir()
    mock_file_path = os.path.join(tmp_dir, "test_client_secret.json")

    with open(mock_file_path, "w") as f:
        json.dump(mock_secrets, f)

    CLIENT_SECRETS_FILE = mock_file_path

# WAŻNE: Tutaj ustawiamy uprawnienia do edycji
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

REDIRECT_URI = "http://127.0.0.1:8000/google/callback/"


def google_login(request: Any) -> HttpResponse:
    """Initiate Google OAuth login flow with offline access."""
    # Wymuś dostęp offline, żeby dostać refresh_token
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Wymuś ekran zgody, żeby dostać refresh token
    )

    request.session["google_auth_state"] = state
    return redirect(authorization_url)


def google_callback(request: Any) -> HttpResponse:
    """Handle Google OAuth callback and store credentials."""
    try:
        state = request.session["google_auth_state"]
    except KeyError:
        # Handle missing session state gracefully
        return redirect("/core/settings/")

    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI)

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds = flow.credentials

    GoogleCredentials.objects.update_or_create(
        user=request.user,
        defaults={
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": " ".join(creds.scopes),
        },
    )

    return redirect("/core/settings/")


@login_required
def settings_view(request: Any) -> HttpResponse:
    """Display and update user profile settings."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist, AttributeError:
        # Fallback jeśli profil nie istnieje (np. stary user)
        profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()

            # Zapisz profil energetyczny z tabeli HTML
            energy_data = {}
            for hour in range(0, 24):
                key = f"energy_{hour:02d}"  # np. energy_09
                val = request.POST.get(key)
                if val:
                    energy_data[f"{hour:02d}"] = int(val)

            profile.energy_profile = energy_data
            profile.save()

            messages.success(request, "Ustawienia zapisane pomyślnie!")
            return redirect("/core/settings/")
        else:
            # Form is invalid, continue to render with errors
            pass
    else:
        form = UserProfileForm(instance=profile)

    return render(
        request,
        "core/settings.html",
        {"form": form, "energy_range": range(0, 24), "current_energy": profile.energy_profile},
    )


@login_required
def dashboard_view(request: Any) -> HttpResponse:
    """Display main dashboard with task statistics and recent projects."""
    today = date.today()

    # Statystyki
    tasks_today_count = Task.objects.filter(status="scheduled").count()  # Uproszczenie, bo scheduled znika po dniu
    tasks_overdue_count = Task.objects.filter(status="overdue").count()
    tasks_inbox_count = Task.objects.filter(status="inbox").count()

    # Ostatnie projekty
    from apps.projects.models import Project

    active_projects = Project.objects.filter(user=request.user, status="active").order_by("-created_at")[:5]

    return render(
        request,
        "core/dashboard.html",
        {
            "tasks_today": tasks_today_count,
            "tasks_overdue": tasks_overdue_count,
            "tasks_inbox": tasks_inbox_count,
            "projects": active_projects,
            "today": today,
        },
    )


@require_http_methods(["POST"])
@login_required
def set_work_mode_view(request: Any) -> HttpResponse:
    """Set user work mode (focus, light, or normal) with appropriate buffers."""
    mode = request.POST.get("mode")
    profile = request.user.profile

    if mode == "focus":
        # Tryb Fokus: Małe bufory + Strategia Deep Work
        profile.morning_buffer_minutes = 15
        profile.between_tasks_buffer_minutes = 0
        profile.current_strategy = "deep_work"

    elif mode == "light":
        # Tryb Luz: Duże bufory + Strategia Rozgrzewka
        profile.morning_buffer_minutes = 45
        profile.between_tasks_buffer_minutes = 15
        profile.current_strategy = "warmup"

    else:  # normal
        profile.morning_buffer_minutes = 30
        profile.between_tasks_buffer_minutes = 5
        profile.current_strategy = "balanced"

    profile.save()

    # Wyświetl informację o trybie i strategii
    label_map = {"deep_work": "Głęboka Praca", "warmup": "Rozgrzewka", "balanced": "Zrównoważony"}
    strat_label = label_map.get(profile.current_strategy, "Standard")

    return HttpResponse(
        f'<span class="badge bg-secondary" title="Strategia: {strat_label}">Tryb: {mode.title()}</span>'
    )
