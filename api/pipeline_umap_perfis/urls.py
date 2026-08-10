from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='umap-perfis-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='umap-perfis-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='umap-perfis-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='umap-perfis-task-status'),
]
