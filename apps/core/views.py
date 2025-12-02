from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserProfileForm
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from .models import GoogleCredentials, UserProfile
import os
from datetime import date
from apps.tasks.models import Task
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse


# Ścieżka do pliku JSON
CLIENT_SECRETS_FILE = os.path.join(settings.BASE_DIR, 'client_secret.json')

# WAŻNE: Tutaj ustawiamy uprawnienia do edycji
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

REDIRECT_URI = 'http://127.0.0.1:8000/core/google/callback/'


def google_login(request):
    # Wymuś dostęp offline, żeby dostać refresh_token
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Wymuś ekran zgody, żeby dostać refresh token
    )

    request.session['google_auth_state'] = state
    return redirect(authorization_url)


def google_callback(request):
    state = request.session['google_auth_state']

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds = flow.credentials

    GoogleCredentials.objects.update_or_create(
        user=request.user,
        defaults={
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': ' '.join(creds.scopes)
        }
    )

    return redirect('settings')


@login_required
def settings_view(request):
    try:
        profile = request.user.profile
    except:
        # Fallback jeśli profil nie istnieje (np. stary user)
        from .models import UserProfile
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
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
            return redirect('settings')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'core/settings.html', {
        'form': form,
        'energy_range': range(0, 24),
        'current_energy': profile.energy_profile
    })


@login_required
def dashboard_view(request):
    today = date.today()

    # Statystyki
    tasks_today_count = Task.objects.filter(status='scheduled').count()  # Uproszczenie, bo scheduled znika po dniu
    tasks_overdue_count = Task.objects.filter(status='overdue').count()
    tasks_inbox_count = Task.objects.filter(status='inbox').count()

    # Ostatnie projekty
    from apps.projects.models import Project
    active_projects = Project.objects.filter(user=request.user, status='active').order_by('-created_at')[:5]

    return render(request, 'core/dashboard.html', {
        'tasks_today': tasks_today_count,
        'tasks_overdue': tasks_overdue_count,
        'tasks_inbox': tasks_inbox_count,
        'projects': active_projects,
        'today': today
    })


@require_http_methods(["POST"])
@login_required
def set_work_mode_view(request):
    mode = request.POST.get('mode')  # 'normal', 'focus', 'light'
    profile = request.user.profile

    if mode == 'focus':
        profile.morning_buffer_minutes = 15
        profile.between_tasks_buffer_minutes = 0  # Bez przerw!
    elif mode == 'light':
        profile.morning_buffer_minutes = 45
        profile.between_tasks_buffer_minutes = 15  # Dużo luzu
    else:  # normal
        profile.morning_buffer_minutes = 30
        profile.between_tasks_buffer_minutes = 5

    profile.save()

    # Zwróć tylko fragment HTML z informacją (np. Toast lub badge)
    return HttpResponse(f'<span class="badge bg-secondary">Tryb: {mode.title()}</span>')