from django.urls import path
from . import views

urlpatterns = [
    path('', views.goal_list_view, name='goal_list'),
    path('new/', views.goal_create_view, name='goal_create'),
    path('<int:pk>/edit/', views.goal_edit_view, name='goal_edit'),

]