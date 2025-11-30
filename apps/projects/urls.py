from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list_view, name='project_list'),
    path('<int:pk>/', views.project_detail_view, name='project_detail'),
    path('new/', views.project_create_view, name='project_create'),
]