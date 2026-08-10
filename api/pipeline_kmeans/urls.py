# api/pipeline_kmeans/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_kmeans_pipeline, name='kmeans-trigger'),
    path('tasks/<uuid:task_id>/status/', views.get_kmeans_task_status, name='kmeans-task-status'),
    # ⭐ NOVO: Rota para listar todas as tasks de K-Means ⭐
    path('tasks/', views.KMeansTaskListView.as_view(), name='kmeans-task-list'),
]
