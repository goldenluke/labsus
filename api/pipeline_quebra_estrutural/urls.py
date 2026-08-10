from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='quebra-estrutural-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='quebra-estrutural-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='quebra-estrutural-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='quebra-estrutural-task-status'),
]
