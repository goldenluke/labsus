from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_perinatal_pipeline, name='perinatal-trigger'),
    path('tasks/', views.PerinatalTaskListView.as_view(), name='perinatal-task-list'),
    path('tasks/<uuid:pk>/', views.PerinatalTaskDetailView.as_view(), name='perinatal-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_perinatal_task_status, name='perinatal-task-status'),
]
