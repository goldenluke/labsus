# api/pipeline_predicao_internacoes/apps.py

from django.apps import AppConfig

class PipelinePredicaoInternacoesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_predicao_internacoes'
    label = 'pipeline_predicao_internacoes' # Rótulo do app para usar em apps.get_model()

    def ready(self):
        # Opcional: Você pode adicionar lógica de inicialização aqui se necessário,
        # mas para Celery tasks, geralmente não é preciso.
        pass
