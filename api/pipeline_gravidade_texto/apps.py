from django.apps import AppConfig


class GravidadeTextoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_gravidade_texto'
    verbose_name = 'NLP: Gravidade por Texto Clínico'
