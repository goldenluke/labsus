from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_cost_prediction, name='custo-internacao-trigger'),
    path('tasks/', views.CustoInternacaoTaskListView.as_view(), name='custo-internacao-task-list'),
    path('tasks/<uuid:pk>/', views.CustoInternacaoTaskDetailView.as_view(), name='custo-internacao-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_cost_task_status, name='custo-internacao-task-status'),
]
