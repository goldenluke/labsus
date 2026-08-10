from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

# Imports locais da pipeline
from .tasks import run_readmission_prediction, run_cox_survival_analysis
from .models import ReadmissaoTaskStatus
from api.serializers import ReadmissaoTaskStatusSerializer # Importa o serializer que criámos

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_readmission_pipeline(request):
    patient_data = request.data.get('patient_data')
    # ⭐ 1. OBTÉM O NOME DO FICHEIRO DO PEDIDO ⭐
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not isinstance(patient_data, dict):
        return Response(
            {'error': 'O corpo da requisição deve conter um objeto JSON na chave "patient_data".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_readmission_prediction.delay(
            user_id=user_id,
            patient_data=patient_data,
            # ⭐ 2. PASSA O NOME DO FICHEIRO PARA A TAREFA ⭐
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline de previsão de readmissão.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_readmission_task_status(request, task_id):
    """
    Verifica e retorna o status de uma tarefa Celery específica.
    """
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


class ReadmissaoTaskListView(generics.ListAPIView):
    """
    Endpoint para listar o histórico de todas as tarefas de previsão de readmissão
    executadas pelo utilizador logado.
    """
    serializer_class = ReadmissaoTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Retorna apenas as tarefas do utilizador que fez a requisição, ordenadas pela mais recente
        return ReadmissaoTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')

    # ⭐ ADICIONE ESTA NOVA CLASSE AO FINAL DO FICHEIRO ⭐
class ReadmissaoTaskDetailView(generics.RetrieveAPIView):
    """
    Endpoint para obter os detalhes completos de uma única tarefa de previsão de readmissão.
    """
    serializer_class = ReadmissaoTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = ReadmissaoTaskStatus.objects.all()
    lookup_field = 'pk' # Diz à view para procurar pelo ID da tarefa (pk)

    def get_queryset(self):
        # Garante que um utilizador só pode ver as suas próprias tarefas
        return ReadmissaoTaskStatus.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_cox_pipeline(request):
    patient_data = request.data.get('patient_data')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not isinstance(patient_data, dict):
        return Response(
            {'error': 'O corpo da requisição deve conter um objeto JSON na chave "patient_data".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_cox_survival_analysis.delay(
            user_id=user_id,
            patient_data=patient_data,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline Cox de readmissão.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
