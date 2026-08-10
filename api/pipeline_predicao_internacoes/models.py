# api/pipeline_predicao_internacoes/models.py

from django.db import models
from django.conf import settings
import uuid

class PredictionTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pendente'),
        ('STARTED', 'Iniciada'),
        ('PROGRESS', 'Em Progresso'),
        ('SUCCESS', 'Sucesso'),
        ('FAILURE', 'Falha'),
        ('REVOKED', 'Revogada'),
    ])
    # Parâmetros da previsão
    ufs = models.JSONField(default=list, help_text="Lista de UFs usadas para a predição.")
    anos_historico = models.JSONField(default=list, help_text="Anos de dados históricos usados para o treinamento.")
    cid_codes = models.JSONField(default=list, help_text="Lista de códigos CID-10 usados para a predição.")
    meses_previsao = models.IntegerField(default=6, help_text="Número de meses previstos no futuro.")

    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='prediction_output_tasks',
                                    help_text="Arquivo CSV de saída com os resultados da previsão.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Previsão {self.task_id} - {self.status}"
