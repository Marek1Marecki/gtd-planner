# apps/tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list_view, name='task_list'),        # to obsługuje /tasks/
    path('new/', views.task_create_view, name='task_create'), # to obsługuje /tasks/new/
    path('search/', views.task_search_view, name='task_search'),
]