from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='sobrevida-tb-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='sobrevida-tb-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='sobrevida-tb-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='sobrevida-tb-task-status'),
]
