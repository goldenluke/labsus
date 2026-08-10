from django.db import models
from django.conf import settings
import uuid


class CustoInternacaoTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    # Parâmetros de entrada
    patient_data = models.JSONField(help_text="Dados da internação usados para a previsão de custo.")

    # Resultados
    custo_previsto = models.FloatField(null=True, blank=True, help_text="Custo previsto da internação (R$).")
    output_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='custo_internacao_tasks',
        help_text="CSV com os dados da previsão de custo."
    )
    output_image_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='custo_internacao_images',
        help_text="Imagem com a explicação SHAP do custo."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Custo Internação {self.task_id} - {self.status}"
