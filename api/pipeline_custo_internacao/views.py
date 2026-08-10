from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_cost_prediction
from .models import CustoInternacaoTaskStatus
from api.serializers import CustoInternacaoTaskStatusSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_cost_prediction(request):
    patient_data = request.data.get('patient_data')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not isinstance(patient_data, dict):
        return Response(
            {'error': 'O corpo da requisição deve conter um objeto JSON na chave "patient_data".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    required_fields = ['DIAS_PERM', 'IDADE', 'DIAG_PRINC', 'PROC_REA']
    missing = [f for f in required_fields if f not in patient_data]
    if missing:
        return Response(
            {'error': f'Campos obrigatórios faltando: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_cost_prediction.delay(
            user_id=user_id,
            patient_data=patient_data,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de previsão de custo.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cost_task_status(request, task_id):
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


class CustoInternacaoTaskListView(generics.ListAPIView):
    serializer_class = CustoInternacaoTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustoInternacaoTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class CustoInternacaoTaskDetailView(generics.RetrieveAPIView):
    serializer_class = CustoInternacaoTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = CustoInternacaoTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return CustoInternacaoTaskStatus.objects.filter(user=self.request.user)
