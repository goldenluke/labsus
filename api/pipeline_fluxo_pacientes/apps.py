from django.apps import AppConfig

class PipelineFluxoPacientesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # ⭐ GARANTA QUE O 'name' SEJA O CAMINHO COMPLETO DA APP ⭐
    name = 'api.pipeline_fluxo_pacientes'
    label = 'pipeline_fluxo_pacientes'
