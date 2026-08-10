from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='rede-comorbidades-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='rede-comorbidades-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='rede-comorbidades-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='rede-comorbidades-task-status'),
]
