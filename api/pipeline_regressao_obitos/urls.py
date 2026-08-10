from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_regressao_obitos_pipeline, name='regressao-obitos-trigger'),
    path('tasks/', views.RegressaoObitosTaskListView.as_view(), name='regressao-obitos-task-list'),
    path('tasks/<uuid:task_id>/status/', views.get_regressao_obitos_task_status, name='regressao-obitos-task-status'),

    # A rota de status individual pode ser adicionada se necessário, seguindo o padrão das outras pipelines
]
