from django.apps import AppConfig


class UmapPerfisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_umap_perfis'
    verbose_name = 'UMAP+HDBSCAN: Perfis Municipais'
