from django.apps import AppConfig


class QuebraEstruturalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_quebra_estrutural'
    verbose_name = 'Quebra Estrutural: Óbitos (Teste de Chow)'
