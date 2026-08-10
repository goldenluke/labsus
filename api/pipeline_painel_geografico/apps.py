from django.apps import AppConfig


class PainelGeograficoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_painel_geografico'
    verbose_name = 'Gerar Painel Geográfico (IVS + CNES)'
