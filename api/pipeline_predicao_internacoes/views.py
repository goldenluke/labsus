# api/pipeline_predicao_internacoes/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics, permissions # Importe generics
from celery.result import AsyncResult
from django.apps import apps
import traceback
import logging

from .tasks import run_prediction_pipeline
from .models import PredictionTaskStatus # Importe o modelo
from api.serializers import PredictionTaskStatusSerializer # Importe o serializer


logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_prediction_pipeline(request):
    ufs = request.data.get('ufs', [])
    anos_historico = request.data.get('anos_historico', [])
    cid_codes = request.data.get('cid_codes', [])
    meses_previsao = request.data.get('meses_previsao', 6)
    output_filename = request.data.get('output_filename', None) # Captura o nome do arquivo de saída

    user_id = request.user.id

    if not ufs:
        return Response({'error': 'Pelo menos uma UF é obrigatória.'}, status=status.HTTP_400_BAD_REQUEST)
    if not anos_historico:
        return Response({'error': 'Pelo menos um ano histórico é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
    if not cid_codes:
        return Response({'error': 'Pelo menos um código CID-10 é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(meses_previsao, int) or meses_previsao <= 0:
        return Response({'error': 'O número de meses de previsão deve ser um inteiro positivo.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task = run_prediction_pipeline.delay(
            ufs=ufs,
            anos_historico=anos_historico,
            cid_codes=cid_codes,
            meses_previsao=meses_previsao,
            user_id=user_id,
            output_filename=output_filename # Passa o nome do arquivo de saída para a task
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Erro ao disparar pipeline de predição de internações: {e}\n{tb}")
        return Response({'error': str(e), 'traceback': tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_prediction_task_status(request, task_id):
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
        response_data['message'] = 'Task foi revogada.'

    return Response(response_data)

# ⭐ NOVO: View para listar todas as tasks de Predição de Internações do usuário logado ⭐
class PredictionTaskListView(generics.ListAPIView):
    serializer_class = PredictionTaskStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = PredictionTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        return queryset
