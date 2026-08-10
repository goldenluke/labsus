from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_regressao_obitos_pipeline
from .models import RegressaoObitosTaskStatus
from api.serializers import RegressaoObitosTaskStatusSerializer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_regressao_obitos_pipeline(request): # ⭐ GARANTA QUE O NOME DA FUNÇÃO SEJA ESTE
    data = request.data
    user_id = request.user.id

    if not all(k in data for k in ['ufs', 'anos', 'diagnostico_cids']):
        return Response({'error': 'Parâmetros ufs, anos e diagnostico_cids são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

    decision_threshold = data.get('decision_threshold', 0.5)

    try:
        task = run_regressao_obitos_pipeline.delay(
            ufs=data['ufs'],
            anos=data['anos'],
            diagnostico_cids=data['diagnostico_cids'],
            comorbidade_cids=data.get('comorbidade_cids'),
            user_id=user_id,
            output_filename=data.get('output_filename'),
            decision_threshold=decision_threshold
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de regressão de óbitos.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_regressao_obitos_task_status(request, task_id):
    task_id_str = str(task_id)
    result = AsyncResult(task_id_str)
    response_data = {
        'task_id': task_id_str,
        'status': result.status,
    }

    if result.status == 'PROGRESS' and isinstance(result.info, dict):
        response_data['progress'] = result.info.get('progress', 0)
        response_data['message'] = result.info.get('message', 'Em progresso...')
    elif result.status == 'SUCCESS':
        response_data['result'] = result.result
        if result.result and 'output_file_id' in result.result:
            response_data['output_file_id'] = result.result['output_file_id']
    elif result.status == 'FAILURE':
        response_data['error'] = str(result.result)
    elif result.status == 'REVOKED':
        response_data['message'] = 'Tarefa foi revogada.'

    return Response(response_data)


class RegressaoObitosTaskListView(generics.ListAPIView):
    serializer_class = RegressaoObitosTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RegressaoObitosTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')
