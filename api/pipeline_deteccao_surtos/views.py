from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
import logging
from celery.result import AsyncResult

from .tasks import run_outbreak_detection
from .models import DeteccaoSurtosTaskStatus
from api.serializers import DeteccaoSurtosTaskStatusSerializer

logger = logging.getLogger(__name__)

GRAVOS_CHOICES = {
    'DENG': 'Dengue',
    'CHIK': 'Chikungunya',
    'ZIKA': 'Zika',
    'MALA': 'Malária',
    'LEPT': 'Leptospirose',
    'HANT': 'Hantavirose',
    'TUBE': 'Tuberculose',
    'MENI': 'Meningite',
    'COQU': 'Coqueluche',
    'HEPA': 'Hepatites Virais',
    'SIFA': 'Sífilis Adquirida',
    'SIFC': 'Sífilis Congênita',
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_gravos(request):
    return Response([{'value': k, 'label': v} for k, v in GRAVOS_CHOICES.items()])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_outbreak_detection(request):
    ufs = request.data.get('ufs', [])
    anos = request.data.get('anos', [])
    agravo = request.data.get('agravo', 'DENG')
    output_filename = request.data.get('output_filename', None)
    user_id = request.user.id

    if not ufs or not isinstance(ufs, list):
        return Response(
            {'error': 'O campo "ufs" deve ser uma lista não vazia (ex: ["TO"]).'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not anos or not isinstance(anos, list):
        return Response(
            {'error': 'O campo "anos" deve ser uma lista não vazia (ex: [2021, 2022, 2023, 2024]).'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if agravo not in GRAVOS_CHOICES:
        return Response(
            {'error': f'agravo inválido. Opções: {", ".join(GRAVOS_CHOICES.keys())}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = run_outbreak_detection.delay(
            user_id=user_id,
            ufs=ufs,
            anos=[int(a) for a in anos],
            agravo=agravo,
            output_filename=output_filename
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar pipeline de detecção de surtos.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_outbreak_task_status(request, task_id):
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


class DeteccaoSurtosTaskListView(generics.ListAPIView):
    serializer_class = DeteccaoSurtosTaskStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DeteccaoSurtosTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class DeteccaoSurtosTaskDetailView(generics.RetrieveAPIView):
    serializer_class = DeteccaoSurtosTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = DeteccaoSurtosTaskStatus.objects.all()
    lookup_field = 'pk'

    def get_queryset(self):
        return DeteccaoSurtosTaskStatus.objects.filter(user=self.request.user)
