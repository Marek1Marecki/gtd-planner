# gtd_calendar/urls.py
from django.contrib import admin
from django.urls import path, include  # upewnij się, że jest include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Tutaj podpinamy nasze aplikacje:
    path('tasks/', include('apps.tasks.urls')),
]