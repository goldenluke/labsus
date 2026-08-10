# api/pipeline_kmeans/apps.py

from django.apps import AppConfig

class PipelineKMeansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_kmeans'
    label = 'pipeline_kmeans' # Rótulo do app para usar em apps.get_model()
