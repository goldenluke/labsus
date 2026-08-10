from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='excesso-mortalidade-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='excesso-mortalidade-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='excesso-mortalidade-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='excesso-mortalidade-task-status'),
]
