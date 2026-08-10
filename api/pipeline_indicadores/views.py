# api/pipeline_indicadores/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated # Este já estava lá, mas não era o suficiente
from rest_framework.response import Response
from rest_framework import status, generics, permissions # ⭐ CORREÇÃO AQUI: Adicionar 'permissions' ⭐
from celery.result import AsyncResult
from django.apps import apps
import traceback
import logging

from .tasks import run_pipeline_indicadores_task, run_integracao_pipeline
from .models import IntegracaoTaskStatus
from api.serializers import IntegracaoTaskStatusSerializer


logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_pipeline_indicadores(request):
    try:
        ufs = request.data.get('ufs', ['TO'])
        anos = request.data.get('anos', [2022])
        arboviroses = request.data.get('arboviroses', ['chikungunya', 'zika'])
        mortalidade = request.data.get('mortalidade', ['circulatorio', 'neoplasias', 'respiratorias', 'diabetes', 'externas', 'covid19'])
        indicadores = request.data.get('indicadores', None)

        task = run_pipeline_indicadores_task.delay(ufs, anos, arboviroses, mortalidade, indicadores)
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Erro na trigger_pipeline_indicadores: {e}")
        print(tb)
        return Response({'error': str(e), 'traceback': tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status_indicadores(request, task_id):
    print(f"Entrou em get_task_status_indicadores para task_id={task_id}")
    task_id_str = str(task_id)
    result = AsyncResult(task_id_str)
    print(f"Status da task: {result.status}")
    response_data = {
        'task_id': task_id_str,
        'status': result.status,
    }

    if result.status == 'PROGRESS' and isinstance(result.info, dict):
        response_data['result'] = result.info
    elif result.status == 'SUCCESS':
        response_data['result'] = result.result
    elif result.status == 'FAILURE':
        response_data['result'] = str(result.result)

    print(f"Response: {response_data}")
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_integracao_pipeline(request):
    ufs = request.data.get('ufs', [])
    anos = request.data.get('anos', [])
    arboviroses = request.data.get('arboviroses', [])
    mortalidade = request.data.get('mortalidade', [])
    indicadores = request.data.get('indicadores', [])
    output_csv_filename = request.data.get('output_csv_filename', None)
    pop_csv_path = request.data.get('pop_csv_path', None)

    user_id = request.user.id

    try:
        task = run_integracao_pipeline.delay(
            ufs=ufs,
            anos=anos,
            arboviroses=arboviroses,
            mortalidade=mortalidade,
            indicadores=indicadores,
            output_csv_filename=output_csv_filename,
            pop_csv_path=pop_csv_path,
            user_id=user_id
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Erro na trigger_integracao_pipeline: {e}")
        print(tb)
        return Response({'error': str(e), 'traceback': tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_integracao_task_status(request, task_id):
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

class IntegracaoTaskListView(generics.ListAPIView):
    serializer_class = IntegracaoTaskStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = IntegracaoTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')

        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        return queryset
