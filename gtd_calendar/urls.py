# gtd_calendar/urls.py
from django.contrib import admin
from django.urls import path, include
from apps.core import views as core_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.dashboard_view, name='home'), # Pusta ścieżka = Home
    # Tutaj podpinamy nasze aplikacje:
    path('tasks/', include('apps.tasks.urls')),
    path('calendar/', include('apps.calendar_app.urls')),
    path('projects/', include('apps.projects.urls')),
    path('reports/', include('apps.reports.urls')),
    path('core/', include('apps.core.urls')),
    path('notes/', include('apps.notes.urls')),
]