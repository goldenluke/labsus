# === Início do arquivo: api/pipeline_kmeans/views.py ===

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from celery.result import AsyncResult
from django.apps import apps
import traceback

from .tasks import run_kmeans_pipeline
from .models import KMeansTaskStatus
from api.serializers import KMeansTaskStatusSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_kmeans_pipeline(request):
    input_file_id = request.data.get('input_file_id')
    n_clusters = request.data.get('n_clusters', 3)
    features_for_clustering = request.data.get('features_for_clustering', [])
    archetype_file_id = request.data.get('archetype_file_id', None)
    output_filename = request.data.get('output_filename', None)

    user_id = request.user.id

    if not input_file_id:
        return Response({'error': 'Parâmetro "input_file_id" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(n_clusters, int) or n_clusters < 2:
        return Response({'error': 'Parâmetro "n_clusters" deve ser um inteiro maior ou igual a 2.'}, status=status.HTTP_400_BAD_REQUEST)

    # A validação que tornava o arquivo de arquétipos obrigatório foi removida daqui.

    try:
        ManagedFile = apps.get_model('api', 'ManagedFile')
        try:
            # Garante que o usuário só pode usar arquivos que ele mesmo enviou
            input_file_instance = ManagedFile.objects.get(id=input_file_id, uploader=request.user)
        except ManagedFile.DoesNotExist:
            return Response({'error': f'Arquivo de entrada ID {input_file_id} não encontrado ou permissão negada.'}, status=status.HTTP_404_NOT_FOUND)

        if archetype_file_id:
            if not ManagedFile.objects.filter(id=archetype_file_id, uploader=request.user).exists():
                return Response({'error': f'Arquivo de arquétipos ID {archetype_file_id} não encontrado ou permissão negada.'}, status=status.HTTP_404_NOT_FOUND)

        task = run_kmeans_pipeline.delay(
            input_file_id=input_file_id,
            n_clusters=n_clusters,
            features_for_clustering=features_for_clustering,
            archetype_file_id=archetype_file_id,
            user_id=user_id,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        tb = traceback.format_exc()
        # Em um ambiente de produção, seria bom logar este erro.
        # Ex: logger.error(f"Erro ao disparar pipeline K-Means: {e}\n{tb}")
        return Response({'error': str(e), 'traceback': tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_kmeans_task_status(request, task_id):
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
        response_data['message'] = 'Task foi revogada.'

    return Response(response_data)


class KMeansTaskListView(generics.ListAPIView):
    """
    View para listar todas as tarefas K-Means pertencentes ao usuário logado.
    """
    serializer_class = KMeansTaskStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = KMeansTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')

        # Filtro opcional por status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        return queryset

# === Fim do arquivo: api/pipeline_kmeans/views.py ===
