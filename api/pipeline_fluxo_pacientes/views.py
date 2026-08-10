from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult # ⭐ 1. Adicione esta importação

from .tasks import run_fluxo_pacientes_pipeline
from .models import FluxoPacientesTaskStatus
from api.serializers import FluxoPacientesTaskStatusSerializer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_fluxo_pacientes_pipeline(request):
    data = request.data
    user_id = request.user.id

    required_params = ['ufs', 'anos', 'diagnostico_cids', 'min_pacientes_fluxo']
    if not all(k in data for k in required_params):
        return Response({'error': 'Parâmetros insuficientes.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task = run_fluxo_pacientes_pipeline.delay(
            user_id=user_id,
            ufs=data['ufs'],
            anos=data['anos'],
            diagnostico_cids=data['diagnostico_cids'],
            min_pacientes_fluxo=data['min_pacientes_fluxo'],
            output_filename=data.get('output_filename')
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de fluxo de pacientes.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ⭐ 2. ADICIONE ESTA NOVA VIEW COMPLETA ⭐
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fluxo_pacientes_task_status(request, task_id):
    """
    Verifica e retorna o status de uma tarefa Celery de fluxo de pacientes.
    """
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


class FluxoPacientesTaskListView(generics.ListAPIView):
    serializer_class = FluxoPacientesTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FluxoPacientesTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')
