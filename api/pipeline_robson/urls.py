from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='robson-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='robson-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='robson-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='robson-task-status'),
]
