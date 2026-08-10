# api/pipeline_indicadores/models.py

from django.db import models
from django.conf import settings
import uuid

# Definição do modelo IntegracaoTaskStatus
class IntegracaoTaskStatus(models.Model):
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
    input_files = models.JSONField(default=list, help_text="Lista de IDs dos ManagedFiles de entrada.")
    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                    help_text="Arquivo CSV de saída consolidado.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Integração {self.task_id} - {self.status}"

# Se você tiver outros modelos neste arquivo (ex: Task), certifique-se de que eles também estão aqui.
# class Task(models.Model):
#    title = models.CharField(max_length=200)
#    completed = models.BooleanField(default=False)
#    created_at = models.DateTimeField(auto_now_add=True)
#    def __str__(self):
#        return self.title
