from django.db import models
from django.conf import settings
import uuid


class SobrevidaPermanenciaTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    parametros = models.JSONField(default=dict, blank=True, help_text="Parâmetros usados para disparar a análise.")
    output_file = models.ForeignKey(
        'api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Um dos arquivos gerados pela análise (ver todos em /api/files/?task_id=)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Sobrevida: Permanência Hospitalar {self.task_id} - {self.status}"
