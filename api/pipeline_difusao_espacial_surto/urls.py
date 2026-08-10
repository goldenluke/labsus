from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='difusao-espacial-surto-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='difusao-espacial-surto-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='difusao-espacial-surto-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='difusao-espacial-surto-task-status'),
]
