# apps/tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list_view, name='task_list'),        # to obsługuje /tasks/
    path('new/', views.task_create_view, name='task_create'), # to obsługuje /tasks/new/
    path('search/', views.task_search_view, name='task_search'),
    path('<int:pk>/complete/', views.task_complete_view, name='task_complete'),
    path('<int:pk>/force-today/', views.task_force_today_view, name='task_force_today'),
    path('<int:pk>/resume/', views.task_resume_view, name='task_resume'),

]