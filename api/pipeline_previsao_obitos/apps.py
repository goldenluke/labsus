from django.apps import AppConfig


class PrevisaoObitosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_previsao_obitos'
    verbose_name = 'Previsão de Óbitos (Prophet)'
