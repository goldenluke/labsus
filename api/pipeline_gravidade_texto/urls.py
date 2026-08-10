from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='gravidade-texto-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='gravidade-texto-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='gravidade-texto-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='gravidade-texto-task-status'),
]
