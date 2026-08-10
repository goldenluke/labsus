from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='hdbscan-estabelecimentos-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='hdbscan-estabelecimentos-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='hdbscan-estabelecimentos-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='hdbscan-estabelecimentos-task-status'),
]
