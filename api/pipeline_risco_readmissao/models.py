from django.db import models
from django.conf import settings
import uuid

class ReadmissaoTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    # Parâmetros de entrada
    patient_data = models.JSONField(help_text="Dados do paciente usados para a previsão.")

    # Resultados
    risk_score = models.FloatField(null=True, blank=True, help_text="Score de risco de readmissão (0 a 1).")
    output_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='readmissao_output_files',
        help_text="Arquivo CSV com o resultado da previsão."
    )
    output_image_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Arquivo de imagem com a explicação SHAP."
    )
    shap_data = models.JSONField(null=True, blank=True, help_text="Dados SHAP ou Cox para gráfico Plotly.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Previsão de Readmissão {self.task_id} - {self.status}"
