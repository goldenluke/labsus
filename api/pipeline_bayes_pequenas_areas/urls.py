from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='bayes-pequenas-areas-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='bayes-pequenas-areas-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='bayes-pequenas-areas-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='bayes-pequenas-areas-task-status'),
]
