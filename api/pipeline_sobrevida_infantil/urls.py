from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_sobrevida_pipeline, name='sobrevida-trigger'),
    path('tasks/', views.SobrevidaTaskListView.as_view(), name='sobrevida-task-list'),
    path('tasks/<uuid:pk>/', views.SobrevidaTaskDetailView.as_view(), name='sobrevida-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_sobrevida_task_status, name='sobrevida-task-status'),
]
