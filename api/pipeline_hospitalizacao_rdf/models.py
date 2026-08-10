from django.db import models
from django.conf import settings
import uuid


class HospitalizacaoRDFTaskStatus(models.Model):
    """Igual em espírito a PredictionTaskStatus/RegressaoObitosTaskStatus --
    a diferença é que esta pipeline não usa pandas/PySUS direto: ela carrega
    a competência solicitada no armazenamento persistente da BPHO (via
    owl/store.py, processo/venv separado) e produz o resultado consultando
    esse armazenamento por SPARQL, não por groupby de DataFrame."""
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pendente'),
        ('STARTED', 'Iniciada'),
        ('PROGRESS', 'Em Progresso'),
        ('SUCCESS', 'Sucesso'),
        ('FAILURE', 'Falha'),
    ])

    uf = models.CharField(max_length=2, help_text="UF da competência do SIH a carregar/consultar.")
    ano = models.IntegerField(help_text="Ano da competência (ex.: 2025).")
    mes = models.IntegerField(help_text="Mês da competência (1-12).")
    grupo = models.CharField(max_length=2, default='RD', help_text="Grupo de arquivo do SIH (RD/RJ/ER).")

    output_file = models.ForeignKey('api.ManagedFile', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='hospitalizacao_rdf_output_tasks',
                                     help_text="CSV com o agregado de Hospitalization por HealthFacility, via SPARQL.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)
    results_summary = models.JSONField(default=dict, null=True, blank=True,
                                        help_text="Totais e contagem por AIHRecordStatus, vindos da consulta SPARQL.")

    def __str__(self):
        return f"Hospitalização RDF {self.task_id} - {self.status}"
