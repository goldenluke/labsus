from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_doencas_cronicas_pipeline, name='doencas-cronicas-trigger'),
    path('tasks/', views.DoencasCronicasTaskListView.as_view(), name='doencas-cronicas-task-list'),
    path('tasks/<uuid:pk>/', views.DoencasCronicasTaskDetailView.as_view(), name='doencas-cronicas-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_doencas_cronicas_task_status, name='doencas-cronicas-task-status'),
]
