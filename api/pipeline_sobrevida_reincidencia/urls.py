from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='sobrevida-reincidencia-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='sobrevida-reincidencia-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='sobrevida-reincidencia-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='sobrevida-reincidencia-task-status'),
]
