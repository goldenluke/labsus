from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='obito-materno-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='obito-materno-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='obito-materno-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='obito-materno-task-status'),
]
