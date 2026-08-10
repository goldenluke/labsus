from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='painel-geografico-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='painel-geografico-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='painel-geografico-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='painel-geografico-task-status'),
]
