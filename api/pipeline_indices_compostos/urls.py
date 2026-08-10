from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger, name='indices-compostos-trigger'),
    path('tasks/', views.TaskListView.as_view(), name='indices-compostos-task-list'),
    path('tasks/<uuid:pk>/', views.TaskDetailView.as_view(), name='indices-compostos-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_task_status, name='indices-compostos-task-status'),
]
