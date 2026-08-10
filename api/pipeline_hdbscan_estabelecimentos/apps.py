from django.apps import AppConfig


class HdbscanEstabelecimentosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_hdbscan_estabelecimentos'
    verbose_name = 'HDBSCAN: Estabelecimentos Atípicos'
