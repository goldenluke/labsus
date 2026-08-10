# api/pipeline_kmeans/models.py

from django.db import models
from django.conf import settings
import uuid

class KMeansTaskStatus(models.Model):
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
    input_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='kmeans_input_tasks',
                                   help_text="Arquivo CSV de indicadores de entrada.")
    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='kmeans_output_tasks',
                                   help_text="Arquivo CSV de saída com rótulos de cluster.")
    n_clusters = models.IntegerField(default=3, help_text="Número de clusters (k).")
    features_for_clustering = models.JSONField(default=list, help_text="Lista de indicadores usados para agrupamento.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"K-Means {self.task_id} - {self.status}"
