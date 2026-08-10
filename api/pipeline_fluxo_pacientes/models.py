from django.db import models
from django.conf import settings
import uuid

class FluxoPacientesTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING', #...
    )

    # Parâmetros da análise
    ufs = models.JSONField(default=list)
    anos = models.JSONField(default=list)
    diagnostico_cids = models.JSONField(default=list)
    # ⭐ CAMPO REMOVIDO DAQUI ⭐
    # diagnostico_nome = models.CharField(max_length=255)
    min_pacientes_fluxo = models.IntegerField(default=5)

    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='fluxo_pacientes_tasks')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        # ⭐ ATUALIZADO PARA NÃO USAR MAIS O NOME DO DIAGNÓSTICO ⭐
        return f"Fluxo de Pacientes ({self.task_id})"
