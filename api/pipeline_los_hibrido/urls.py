from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_los_prediction, name='los-hibrido-trigger'),
    path('tasks/', views.LosHibridoTaskListView.as_view(), name='los-hibrido-task-list'),
    path('tasks/<uuid:pk>/', views.LosHibridoTaskDetailView.as_view(), name='los-hibrido-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_los_task_status, name='los-hibrido-task-status'),
]
