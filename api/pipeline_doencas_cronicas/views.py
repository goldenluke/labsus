from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_doencas_cronicas
from .models import DoencasCronicasTaskStatus
from api.serializers import DoencasCronicasTaskStatusSerializer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_doencas_cronicas_pipeline(request):
    uf = request.data.get('uf')
    cid_doenca = request.data.get('cid_doenca', 'I50')
    ano_snapshot = request.data.get('ano_snapshot')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not uf or not ano_snapshot:
        return Response(
            {'error': 'Os campos "uf" e "ano_snapshot" são obrigatórios.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_doencas_cronicas.delay(
            user_id=user_id,
            uf=uf,
            cid_doenca=cid_doenca,
            ano_snapshot=int(ano_snapshot),
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de doenças crônicas.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doencas_cronicas_task_status(request, task_id):
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


class DoencasCronicasTaskListView(generics.ListAPIView):
    serializer_class = DoencasCronicasTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DoencasCronicasTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class DoencasCronicasTaskDetailView(generics.RetrieveAPIView):
    serializer_class = DoencasCronicasTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = DoencasCronicasTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return DoencasCronicasTaskStatus.objects.filter(user=self.request.user)
