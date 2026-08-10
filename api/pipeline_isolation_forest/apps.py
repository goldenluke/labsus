from django.apps import AppConfig


class IsolationForestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.pipeline_isolation_forest'
    verbose_name = 'Isolation Forest: Auditoria Financeira'
