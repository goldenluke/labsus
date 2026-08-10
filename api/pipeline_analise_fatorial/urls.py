from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='analise-fatorial-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='analise-fatorial-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='analise-fatorial-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='analise-fatorial-task-status'),
]
