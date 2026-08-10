from django.apps import AppConfig


class PrevisaoNascimentosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_previsao_nascimentos'
    verbose_name = 'Previsão de Nascimentos (Prophet)'
