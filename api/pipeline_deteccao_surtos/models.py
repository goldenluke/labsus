from django.db import models
from django.conf import settings
import uuid


class DeteccaoSurtosTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    # Parâmetros de entrada
    ufs = models.JSONField(help_text="Lista de UFs analisadas.")
    anos = models.JSONField(help_text="Anos históricos usados.")
    agravo = models.CharField(max_length=10, help_text="Código do agravo (DENG, CHIK, etc).")

    # Resultados
    total_alertas = models.IntegerField(default=0, help_text="Total de semanas/municípios em surto.")
    output_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        help_text="CSV com o relatório de alertas."
    )
    chart_data_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='chart_data_tasks',
        help_text="CSV com série temporal completa por município para gráficos."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Detecção Surtos {self.task_id} - {self.status}"
