from django.urls import path
from . import views

urlpatterns = [
    path('', views.goal_list_view, name='goal_list'),

]