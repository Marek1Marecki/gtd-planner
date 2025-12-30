from django.urls import path
from . import views

urlpatterns = [
    path('widget/', views.habit_list_widget, name='habit_widget'),
    path('<int:pk>/complete/', views.habit_complete_view, name='habit_complete'),
]