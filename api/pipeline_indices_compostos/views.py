from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging

from celery.result import AsyncResult

from .tasks import run_indice_composto
from .models import IndiceCompostoTaskStatus, INDICES_VALIDOS
from api.serializers import IndiceCompostoTaskStatusSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger(request):
    parametros = dict(request.data)
    indice = str(parametros.get('indice', '')).lower()

    if indice not in INDICES_VALIDOS:
        return Response(
            {'error': f"Índice '{indice}' inválido. Opções: {', '.join(INDICES_VALIDOS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    parametros['indice'] = indice
    user_id = request.user.id

    try:
        task = run_indice_composto.delay(user_id=user_id, parametros=parametros)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar cálculo de índice composto.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status(request, task_id):
    task_id_str = str(task_id)
    result = AsyncResult(task_id_str)
    response_data = {'task_id': task_id_str, 'status': result.status}
    if result.status == 'PROGRESS' and isinstance(result.info, dict):
        response_data['progress'] = result.info.get('progress', 0)
        response_data['message'] = result.info.get('message', 'Em progresso...')
    elif result.status == 'SUCCESS':
        response_data['result'] = result.result
    elif result.status == 'FAILURE':
        response_data['error'] = str(result.result)
    return Response(response_data)


class TaskListView(generics.ListAPIView):
    serializer_class = IndiceCompostoTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = IndiceCompostoTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')
        indice = self.request.query_params.get('indice')
        if indice:
            qs = qs.filter(indice=indice.lower())
        return qs


class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = IndiceCompostoTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = IndiceCompostoTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return IndiceCompostoTaskStatus.objects.filter(user=self.request.user)
