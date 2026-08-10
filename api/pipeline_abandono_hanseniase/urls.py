from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='abandono-hanseniase-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='abandono-hanseniase-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='abandono-hanseniase-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='abandono-hanseniase-task-status'),
]
