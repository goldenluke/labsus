from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='previsao-obitos-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='previsao-obitos-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='previsao-obitos-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='previsao-obitos-task-status'),
]
