from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='rede-especializacao-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='rede-especializacao-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='rede-especializacao-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='rede-especializacao-task-status'),
]
