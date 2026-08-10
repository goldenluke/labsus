from rest_framework.decorators import api_view, permission_classes
from api.permissions import HasBphoAccess
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_hospitalizacao_rdf_pipeline
from .models import HospitalizacaoRDFTaskStatus
from api.serializers import HospitalizacaoRDFTaskStatusSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_hospitalizacao_rdf_pipeline(request):
    data = request.data
    user_id = request.user.id

    if not all(k in data for k in ['uf', 'ano', 'mes']):
        return Response({'error': 'Parâmetros uf, ano e mes são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task = run_hospitalizacao_rdf_pipeline.delay(
            uf=data['uf'],
            ano=int(data['ano']),
            mes=int(data['mes']),
            grupo=data.get('grupo', 'RD'),
            user_id=user_id,
            output_filename=data.get('output_filename'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de hospitalização RDF.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([HasBphoAccess])
def get_hospitalizacao_rdf_task_status(request, task_id):
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


class HospitalizacaoRDFTaskListView(generics.ListAPIView):
    serializer_class = HospitalizacaoRDFTaskStatusSerializer
    permission_classes = [HasBphoAccess]

    def get_queryset(self):
        return HospitalizacaoRDFTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class HospitalizacaoRDFTaskDetailView(generics.RetrieveAPIView):
    serializer_class = HospitalizacaoRDFTaskStatusSerializer
    permission_classes = [HasBphoAccess]
    lookup_field = 'pk'

    def get_queryset(self):
        return HospitalizacaoRDFTaskStatus.objects.filter(user=self.request.user)
