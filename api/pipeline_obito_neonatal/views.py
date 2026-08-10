from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging

from celery.result import AsyncResult

from .tasks import run_obito_neonatal
from .models import ObitoNeonatalTaskStatus
from api.serializers import ObitoNeonatalTaskStatusSerializer
from api.models import ManagedFile

logger = logging.getLogger(__name__)

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
            parametros[campo] = ManagedFile.objects.get(pk=file_id).file.path
        except ManagedFile.DoesNotExist:
            return Response({'error': f"Arquivo referenciado em '{campo}' não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task = run_obito_neonatal.delay(user_id=user_id, parametros=parametros)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar pipeline obito-neonatal.")
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
    serializer_class = ObitoNeonatalTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ObitoNeonatalTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = ObitoNeonatalTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = ObitoNeonatalTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return ObitoNeonatalTaskStatus.objects.filter(user=self.request.user)
