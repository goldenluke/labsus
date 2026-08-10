from django.urls import path
from . import views

urlpatterns = [
    # Rota para disparar a pipeline: POST para /api/pipelines/risco-readmissao/trigger/
    path('trigger/', views.trigger_readmission_pipeline, name='readmissao-trigger'),

    # Rota para disparar a pipeline Cox: POST para /api/pipelines/risco-readmissao/cox-trigger/
    path('cox-trigger/', views.trigger_cox_pipeline, name='cox-trigger'),

    # Rota para listar o histórico de tarefas: GET para /api/pipelines/risco-readmissao/tasks/
    path('tasks/', views.ReadmissaoTaskListView.as_view(), name='readmissao-task-list'),
    path('tasks/<uuid:pk>/', views.ReadmissaoTaskDetailView.as_view(), name='readmissao-task-detail'),

    # Rota para verificar o status de uma tarefa: GET para /api/pipelines/risco-readmissao/tasks/<task_id>/status/
    path('tasks/<uuid:task_id>/status/', views.get_readmission_task_status, name='readmissao-task-status'),
]
