from django.db import models
from django.conf import settings
import uuid


class LosHibridoTaskStatus(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    # Parâmetros de entrada
    patient_data = models.JSONField(help_text="Dados da internação usados para a previsão de LOS.")
    departamento = models.CharField(
        max_length=20,
        choices=[
            ('Cirurgia', 'Cirurgia'),
            ('Clinica_Medica', 'Clínica Médica'),
            ('Obstetricia', 'Obstetrícia'),
            ('Pediatria', 'Pediatria'),
        ],
        help_text="Departamento/clínica hospitalar."
    )

    # Resultados
    permanencia_classificada = models.CharField(
        max_length=10, null=True, blank=True,
        help_text="Classificação: 'Curta' ou 'Longa'."
    )
    probabilidade_longa = models.FloatField(
        null=True, blank=True,
        help_text="Probabilidade de permanência longa (classificador)."
    )
    previsao_dias = models.FloatField(
        null=True, blank=True,
        help_text="Previsão de dias de permanência (regressor)."
    )
    output_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='los_hibrido_tasks',
        help_text="CSV com o resultado da previsão."
    )
    output_image_file = models.ForeignKey(
        'api.ManagedFile',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='los_hibrido_images',
        help_text="Imagem SHAP da explicação."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"LOS Híbrido {self.task_id} - {self.status}"
