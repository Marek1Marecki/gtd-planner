# apps/reports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('review/', views.weekly_review_view, name='weekly_review'),
]