from django.db import models
from django.conf import settings
import uuid

class RegressaoObitosTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pendente'),
        ('STARTED', 'Iniciada'),
        ('PROGRESS', 'Em Progresso'),
        ('SUCCESS', 'Sucesso'),
        ('FAILURE', 'Falha'),
    ])

    # Parâmetros da análise
    ufs = models.JSONField(default=list, help_text="Lista de UFs usadas para a análise.")
    anos = models.JSONField(default=list, help_text="Anos de dados históricos usados.")
    diagnostico_cids = models.JSONField(default=list, help_text="Lista de CIDs para o diagnóstico principal.")
    comorbidade_cids = models.JSONField(default=list, null=True, blank=True, help_text="(Opcional) Lista de CIDs para a comorbidade.")
    decision_threshold = models.FloatField(default=0.5, help_text="Limiar de probabilidade para classificar como óbito.")

    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='regressao_obitos_output_tasks',
                                      help_text="Arquivo CSV de saída com as predições de risco.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)
    results_summary = models.JSONField(default=dict, null=True, blank=True, help_text="Resumo dos resultados, como AUC e coeficientes.")

    def __str__(self):
        return f"Regressão Risco de Óbito {self.task_id} - {self.status}"
