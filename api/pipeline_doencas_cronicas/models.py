from django.db import models
from django.conf import settings
import uuid

class DoencasCronicasTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    uf = models.CharField(max_length=2, help_text="UF analisada.")
    cid_doenca = models.CharField(max_length=10, default='I50', help_text="CID-10 da doença crônica analisada.")
    ano_snapshot = models.IntegerField(help_text="Ano de referência para a previsão de hospitalização.")

    n_pacientes_coorte = models.IntegerField(null=True, blank=True, help_text="Nº de pacientes na coorte pontuada.")
    roc_auc = models.FloatField(null=True, blank=True, help_text="AUC do modelo no conjunto de teste.")
    shap_data = models.JSONField(null=True, blank=True, help_text="Importância global de features para gráfico Plotly.")

    output_file = models.ForeignKey(
        'api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Arquivo CSV com a coorte pontuada."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Doenças Crônicas {self.task_id} - {self.status}"
