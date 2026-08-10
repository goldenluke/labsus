from django.db import models
from django.conf import settings
import uuid

# Um único modelo de status atende aos 10 índices (HSRI, HNFI, MECI, CCI,
# HAE, HVS, TERI, PHSI, HSSI, HEI) — o campo `indice` identifica qual
# src.indices.<indice> foi executado. Evita criar 10 apps Django quase
# idênticos, já que os 10 índices compartilham a mesma forma de disparo
# (ufs/anos) e o mesmo dashboard genérico no frontend.

INDICES_VALIDOS = ['hsri', 'hnfi', 'meci', 'cci', 'hae', 'hvs', 'teri', 'phsi', 'hssi', 'hei']


class IndiceCompostoTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    indice = models.CharField(max_length=10, choices=[(i, i.upper()) for i in INDICES_VALIDOS])
    status = models.CharField(max_length=20, default='PENDING')
    parametros = models.JSONField(default=dict, blank=True, help_text="Parâmetros usados para disparar a análise.")
    output_file = models.ForeignKey(
        'api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Arquivo CSV gerado pela análise."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.indice.upper()} {self.task_id} - {self.status}"
