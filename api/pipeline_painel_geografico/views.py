from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging

from celery.result import AsyncResult

from .tasks import run_painel_geografico
from .models import PainelGeograficoTaskStatus
from api.serializers import PainelGeograficoTaskStatusSerializer

logger = logging.getLogger(__name__)

# Diferente da maioria das pipelines de Modelagem Avançada, esta não recebe
# nenhum arquivo já processado como entrada — só UFs/ano. As fontes (IVS do
# IPEA, bundled em referencia/ipea/, e CNES via pysus) são resolvidas
# inteiramente no próprio script.
CAMPOS_ARQUIVO = []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger(request):
    parametros = dict(request.data)
    user_id = request.user.id

    for campo in CAMPOS_ARQUIVO:
        file_id = parametros.get(campo)
        if not file_id:
            return Response({'error': f"O campo '{campo}' (arquivo) é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task = run_painel_geografico.delay(user_id=user_id, parametros=parametros)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar pipeline painel-geografico.")
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
    serializer_class = PainelGeograficoTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PainelGeograficoTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = PainelGeograficoTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = PainelGeograficoTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return PainelGeograficoTaskStatus.objects.filter(user=self.request.user)
