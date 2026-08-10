from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='rdd-peso-nascer-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='rdd-peso-nascer-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='rdd-peso-nascer-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='rdd-peso-nascer-task-status'),
]
