from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='binomial-negativa-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='binomial-negativa-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='binomial-negativa-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='binomial-negativa-task-status'),
]
