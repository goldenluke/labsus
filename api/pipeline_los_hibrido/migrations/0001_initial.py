from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LosHibridoTaskStatus',
            fields=[
                ('task_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(default='PENDING', max_length=20)),
                ('patient_data', models.JSONField(help_text='Dados da internação usados para a previsão de LOS.')),
                ('departamento', models.CharField(choices=[('Cirurgia', 'Cirurgia'), ('Clinica_Medica', 'Clínica Médica'), ('Obstetricia', 'Obstetrícia'), ('Pediatria', 'Pediatria')], help_text='Departamento/clínica hospitalar.', max_length=20)),
                ('permanencia_classificada', models.CharField(blank=True, help_text="Classificação: 'Curta' ou 'Longa'.", max_length=10, null=True)),
                ('probabilidade_longa', models.FloatField(blank=True, help_text='Probabilidade de permanência longa (classificador).', null=True)),
                ('previsao_dias', models.FloatField(blank=True, help_text='Previsão de dias de permanência (regressor).', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('message', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('output_file', models.ForeignKey(blank=True, help_text='CSV com o resultado da previsão.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='los_hibrido_tasks', to='api.managedfile')),
                ('output_image_file', models.ForeignKey(blank=True, help_text='Imagem SHAP da explicação.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='los_hibrido_images', to='api.managedfile')),
            ],
            options={
                'verbose_name': 'LOS Híbrido Task Status',
                'verbose_name_plural': 'LOS Híbrido Task Statuses',
            },
        ),
    ]
