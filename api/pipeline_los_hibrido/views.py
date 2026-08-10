from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_los_prediction, DEPARTAMENTOS
from .models import LosHibridoTaskStatus
from api.serializers import LosHibridoTaskStatusSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_los_prediction(request):
    patient_data = request.data.get('patient_data')
    departamento = request.data.get('departamento')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not isinstance(patient_data, dict):
        return Response(
            {'error': 'O corpo da requisição deve conter um objeto JSON na chave "patient_data".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if departamento not in DEPARTAMENTOS:
        return Response(
            {'error': f'Departamento inválido. Opções: {", ".join(DEPARTAMENTOS)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    required_fields = ['IDADE', 'UTI_MES_TO', 'LEITHOSP', 'COMPLEXIDADE_MEDIA', 'SEXO', 'CAR_INT', 'TP_UNID', 'ATIVIDAD', 'CAPITULO_CID']
    missing = [f for f in required_fields if f not in patient_data]
    if missing:
        return Response(
            {'error': f'Campos obrigatórios faltando: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_los_prediction.delay(
            user_id=user_id,
            patient_data=patient_data,
            departamento=departamento,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline LOS Híbrido.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_los_task_status(request, task_id):
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


class LosHibridoTaskListView(generics.ListAPIView):
    serializer_class = LosHibridoTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LosHibridoTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class LosHibridoTaskDetailView(generics.RetrieveAPIView):
    serializer_class = LosHibridoTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = LosHibridoTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return LosHibridoTaskStatus.objects.filter(user=self.request.user)
