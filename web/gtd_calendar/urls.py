# gtd_calendar/urls.py
from apps.core import views as core_views
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path("health/", lambda r: HttpResponse("OK")),
    path("admin/", admin.site.urls),
    path("", core_views.dashboard_view, name="home"),  # Pusta ścieżka = Home
    path("accounts/", include("django.contrib.auth.urls")),
    # Tutaj podpinamy nasze aplikacje:
    path("tasks/", include("apps.tasks.urls")),
    path("calendar/", include("apps.calendar_app.urls")),
    path("projects/", include("apps.projects.urls")),
    path("reports/", include("apps.reports.urls")),
    path("core/", include("apps.core.urls")),
    path("notes/", include("apps.notes.urls")),
    path("habits/", include("apps.habits.urls")),
    path("goals/", include("apps.goals.urls")),
]
