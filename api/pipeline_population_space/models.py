from django.db import models
from django.conf import settings
import uuid


class PopulationSpaceTaskStatus(models.Model):
    """Igual em espírito a HospitalizacaoRDFTaskStatus -- a diferença é que esta
    pipeline não consulta a BPHO diretamente: ela chama o PopulationSpace
    (biospace/plugins/population/, venv próprio) via subprocess, que por sua vez
    consulta a BPHO (SPARQL) e o parquet bruto do SIH (pandas/PySUS), e roda
    fenotipagem (KMeans) sobre o resultado."""

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pendente'),
        ('STARTED', 'Iniciada'),
        ('PROGRESS', 'Em Progresso'),
        ('SUCCESS', 'Sucesso'),
        ('FAILURE', 'Falha'),
    ])

    facility_specs = models.JSONField(
        default=list,
        help_text="Lista de {facility_uri, ano, mes, uf} carregados nesta execução.",
    )
    k = models.IntegerField(default=3, help_text="Número de clusters (KMeans) usado.")

    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='population_space_output_tasks',
                                     help_text="CSV com indicadores + cluster de fenótipo por estabelecimento.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)
    results_summary = models.JSONField(default=dict, null=True, blank=True,
                                        help_text="Saída completa do population_cli.py cluster (JSON).")

    def __str__(self):
        return f"PopulationSpace {self.task_id} - {self.status}"
