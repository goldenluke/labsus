# api/pipeline_indicadores/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_pipeline_indicadores, name='pipeline-trigger'),
    path('tasks/<str:task_id>/status/', views.get_task_status_indicadores, name='task-status'),

    path('integracao/trigger/', views.trigger_integracao_pipeline, name='integracao-trigger'),
    path('integracao/tasks/<uuid:task_id>/status/', views.get_integracao_task_status, name='integracao-task-status'),
    # ⭐ NOVO: Rota para listar todas as tasks de integração ⭐
    path('integracao/tasks/', views.IntegracaoTaskListView.as_view(), name='integracao-task-list'),
]
