from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
    path("google/login/", views.google_login, name="google_login"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("set-mode/", views.set_work_mode_view, name="set_work_mode"),
]
