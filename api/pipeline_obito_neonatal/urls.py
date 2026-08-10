from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='obito-neonatal-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='obito-neonatal-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='obito-neonatal-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='obito-neonatal-task-status'),
]
