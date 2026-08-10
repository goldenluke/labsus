from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_perinatal_risk
from .models import PerinatalTaskStatus
from api.serializers import PerinatalTaskStatusSerializer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_perinatal_pipeline(request):
    patient_data = request.data.get('patient_data')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not isinstance(patient_data, dict):
        return Response(
            {'error': 'O corpo da requisição deve conter um objeto JSON na chave "patient_data".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_perinatal_risk.delay(
            user_id=user_id,
            patient_data=patient_data,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de risco perinatal.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_perinatal_task_status(request, task_id):
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
    elif result.status == 'FAILURE':
        response_data['error'] = str(result.result)

    return Response(response_data)


class PerinatalTaskListView(generics.ListAPIView):
    serializer_class = PerinatalTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PerinatalTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class PerinatalTaskDetailView(generics.RetrieveAPIView):
    serializer_class = PerinatalTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = PerinatalTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return PerinatalTaskStatus.objects.filter(user=self.request.user)
