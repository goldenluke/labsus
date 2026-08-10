from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='kotelchuck-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='kotelchuck-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='kotelchuck-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='kotelchuck-task-status'),
]
