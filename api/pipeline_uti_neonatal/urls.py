from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='uti-neonatal-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='uti-neonatal-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='uti-neonatal-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='uti-neonatal-task-status'),
]
