from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.apps import apps
import logging

from api.models import FileType
from api.utils.modelagem_runner import montar_dir_saida, executar_indice_composto, registrar_arquivos_gerados

logger = logging.getLogger(__name__)

SLUG = "indices-compostos"


@shared_task(bind=True, time_limit=7200, soft_time_limit=6900)
def run_indice_composto(self, user_id, parametros):
    """Uma única task Celery atende aos 10 índices de 2ª camada — o
    parâmetro `indice` seleciona qual src.indices.<indice> executar.
    TERI e PHSI, por operarem sobre vários anos, têm um limite de tempo
    maior (2h) do que o padrão das demais pipelines (1h)."""
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    StatusModel = apps.get_model('pipeline_indices_compostos', 'IndiceCompostoTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    indice = parametros.get('indice', '').lower()

    task_status_entry, _ = StatusModel.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'indice': indice, 'status': 'STARTED', 'parametros': parametros}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Iniciando cálculo do {indice.upper()}...'})
        dir_saida = montar_dir_saida(SLUG, task_id)

        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Baixando dados e calculando componentes (pode levar vários minutos)...'})
        executar_indice_composto(indice, parametros, dir_saida)

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Registrando resultados...'})
        arquivos = registrar_arquivos_gerados(dir_saida, task_id, user, FileType.INDICE_COMPOSTO, ManagedFile)

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"{indice.upper()} calculado. {len(arquivos)} arquivo(s) gerado(s)."
        if arquivos:
            task_status_entry.output_file = arquivos[0]
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'indice': indice,
            'arquivos_gerados': [{'id': a.id, 'filename': a.filename, 'file_type': a.file_type} for a in arquivos],
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Tempo limite excedido no índice {indice} ({task_id}).")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = 'Tempo limite excedido. Tente com menos UFs/anos.'
        task_status_entry.save()
        return {'status': 'FAILURE', 'message': task_status_entry.message}

    except Exception as e:
        logger.exception(f"Falha ao calcular o índice {indice} ({task_id}).")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
