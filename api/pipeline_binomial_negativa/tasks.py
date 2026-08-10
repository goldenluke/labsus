from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.apps import apps
import logging

from api.models import FileType
from api.utils.modelagem_runner import montar_dir_saida, executar_modulo_modelagem, registrar_arquivos_gerados

logger = logging.getLogger(__name__)

MODULO_SRC = "binomial_negativa_determinantes_internacao"
SLUG = "binomial-negativa"


@shared_task(bind=True, time_limit=3600, soft_time_limit=3300)
def run_binomial_negativa(self, user_id, parametros):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    StatusModel = apps.get_model('pipeline_binomial_negativa', 'BinomialNegativaTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = StatusModel.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'status': 'STARTED', 'parametros': parametros}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Iniciando análise...'})
        dir_saida = montar_dir_saida(SLUG, task_id)

        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Baixando dados e executando o modelo (pode levar alguns minutos)...'})
        executar_modulo_modelagem(MODULO_SRC, parametros, dir_saida)

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Registrando resultados...'})
        arquivos = registrar_arquivos_gerados(dir_saida, task_id, user, FileType.BINOMIAL_NEGATIVA, ManagedFile)

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Análise concluída. {len(arquivos)} arquivo(s) gerado(s)."
        if arquivos:
            task_status_entry.output_file = arquivos[0]
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'arquivos_gerados': [{'id': a.id, 'filename': a.filename, 'file_type': a.file_type} for a in arquivos],
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Tempo limite excedido na pipeline {SLUG} {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = 'Tempo limite excedido. Tente com um período menor.'
        task_status_entry.save()
        return {'status': 'FAILURE', 'message': task_status_entry.message}

    except Exception as e:
        logger.exception(f"Falha na pipeline {SLUG} {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
