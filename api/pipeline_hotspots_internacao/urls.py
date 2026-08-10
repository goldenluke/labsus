from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='hotspots-internacao-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='hotspots-internacao-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='hotspots-internacao-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='hotspots-internacao-task-status'),
]
