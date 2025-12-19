# apps/tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list_view, name='task_list'),        # to obsługuje /tasks/
    path('new/', views.task_create_view, name='task_create'), # to obsługuje /tasks/new/
    path('<int:pk>/edit/', views.task_edit_view, name='task_edit'),
    path('search/', views.task_search_view, name='task_search'),
    path('<int:pk>/complete/', views.task_complete_view, name='task_complete'),
    path('<int:pk>/force-today/', views.task_force_today_view, name='task_force_today'),
    path('<int:pk>/resume/', views.task_resume_view, name='task_resume'),
    path('<int:task_id>/checklist/add/', views.checklist_add_view, name='checklist_add'),
    path('checklist/<int:item_id>/toggle/', views.checklist_toggle_view, name='checklist_toggle'),
    path('checklist/<int:item_id>/delete/', views.checklist_delete_view, name='checklist_delete'),
    path('<int:pk>/detail_hx/', views.task_detail_hx_view, name='task_detail_hx'),
    path('<int:pk>/tiny-step/', views.task_tiny_step_view, name='task_tiny_step'),
    path('<int:pk>/split/', views.task_split_view, name='task_split'),
    path('<int:pk>/recurrence/', views.task_recurrence_view, name='task_recurrence'),

]