# api/pipeline_indicadores/apps.py

from django.apps import AppConfig

class PipelineIndicadoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_indicadores' # Nome completo do app
    label = 'pipeline_indicadores' # Você pode ter esquecido de adicionar ou o nome está diferente
