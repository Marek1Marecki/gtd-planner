# apps/reports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard_view, name='reports_dashboard'), # Główna strona raportów
    path('api/stats/', views.stats_api_view, name='stats_api'),       # Dane JSON
    path('review/', views.weekly_review_view, name='weekly_review'),  # Przegląd
]