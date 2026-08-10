from django.db import models
from django.conf import settings
import uuid

class SobrevidaInfantilTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    patient_data = models.JSONField(help_text="Dados SINASC do recém-nascido.")

    mortality_probability = models.FloatField(null=True, blank=True, help_text="Probabilidade de óbito (0 a 1).")
    risk_classification = models.CharField(max_length=20, null=True, blank=True, help_text="Classificação: BAIXO, MODERADO, ALTO.")
    shap_data = models.JSONField(null=True, blank=True, help_text="Dados SHAP para gráfico Plotly.")

    output_file = models.ForeignKey(
        'api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Arquivo CSV com o resultado."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Sobrevida Infantil {self.task_id} - {self.status}"
