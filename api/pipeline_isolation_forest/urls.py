from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='isolation-forest-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='isolation-forest-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='isolation-forest-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='isolation-forest-task-status'),
]
