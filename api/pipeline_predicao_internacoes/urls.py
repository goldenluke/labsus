# api/pipeline_predicao_internacoes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_prediction_pipeline, name='prediction-trigger'),
    path('tasks/<uuid:task_id>/status/', views.get_prediction_task_status, name='prediction-task-status'),
    # ⭐ NOVO: Rota para listar todas as tasks de Predição ⭐
    path('tasks/', views.PredictionTaskListView.as_view(), name='prediction-task-list'),
]
