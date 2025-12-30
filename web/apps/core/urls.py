from django.urls import path
from . import views
from apps.core import views as core_views


urlpatterns = [
    path('settings/', views.settings_view, name='settings'),
    path('core/google/login/', core_views.google_login, name='google_login'),
    path('core/google/callback/', core_views.google_callback, name='google_callback'),
    path('set-mode/', views.set_work_mode_view, name='set_work_mode'),
]