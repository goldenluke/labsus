from django.apps import AppConfig


class PrevisaoProducaoAmbulatorialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_previsao_producao_ambulatorial'
    verbose_name = 'Previsão de Produção Ambulatorial (Prophet)'
