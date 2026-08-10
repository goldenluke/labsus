from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='moran-bivariado-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='moran-bivariado-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='moran-bivariado-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='moran-bivariado-task-status'),
]
