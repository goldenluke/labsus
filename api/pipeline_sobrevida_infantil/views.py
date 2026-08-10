from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_infant_survival
from .models import SobrevidaInfantilTaskStatus
from api.serializers import SobrevidaInfantilTaskStatusSerializer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sobrevida_pipeline(request):
    patient_data = request.data.get('patient_data')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not isinstance(patient_data, dict):
        return Response(
            {'error': 'O corpo da requisição deve conter um objeto JSON na chave "patient_data".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_infant_survival.delay(
            user_id=user_id,
            patient_data=patient_data,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de sobrevida infantil.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sobrevida_task_status(request, task_id):
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


class SobrevidaTaskListView(generics.ListAPIView):
    serializer_class = SobrevidaInfantilTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SobrevidaInfantilTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class SobrevidaTaskDetailView(generics.RetrieveAPIView):
    serializer_class = SobrevidaInfantilTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = SobrevidaInfantilTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return SobrevidaInfantilTaskStatus.objects.filter(user=self.request.user)
