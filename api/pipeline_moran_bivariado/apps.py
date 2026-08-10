from django.apps import AppConfig


class MoranBivariadoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_moran_bivariado'
    verbose_name = 'Moran Bivariado: IVS x Mortalidade'
