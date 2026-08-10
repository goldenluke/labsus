import logging
import re

import requests
from celery.result import AsyncResult
from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from api.permissions import HasBphoAccess
from rest_framework.response import Response

from api.serializers import PopulationSpaceTaskStatusSerializer

from .models import PopulationSpaceTaskStatus
from .tasks import (
    _run_population_cli,
    run_population_anomaly_pipeline,
    run_population_causal_pipeline,
    run_population_classify_pipeline,
    run_population_compare_pipeline,
    run_population_predict_uncertainty_pipeline,
    run_population_risk_pipeline,
    run_population_space_pipeline,
    run_population_transitions_pipeline,
    run_population_survival_pipeline,
    run_population_intervene_pipeline,
    run_population_graph_pipeline,
    run_population_factor_pipeline,
    run_population_topology_pipeline,
    run_population_early_warning_pipeline,
    run_population_gnn_pipeline,
    run_population_dynamics_pipeline,
    run_population_per_capita_pipeline,
    run_population_municipio_pipeline,
    run_population_notificacao_pipeline,
    run_population_familia_pipeline,
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_space_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list):
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf})."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    representation = data.get('representation', 'hospital')
    if representation not in ('hospital', 'primary_care'):
        return Response(
            {'error': "Campo 'representation' deve ser 'hospital' ou 'primary_care'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_space_pipeline.delay(
            facility_specs=facility_specs,
            k=int(data.get('k', 3)),
            user_id=request.user.id,
            output_filename=data.get('output_filename'),
            representation=representation,
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a pipeline PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_compare_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    geometry = data.get('geometry', 'euclidean')
    if geometry not in ('euclidean', 'mahalanobis', 'cosine', 'dtw'):
        return Response(
            {'error': "Campo 'geometry' deve ser um de: euclidean, mahalanobis, cosine, dtw."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 2:
        return Response(
            {'error': "Campo 'facilities' é obrigatório, com pelo menos 2 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if geometry == 'dtw':
        for f in facility_specs:
            if len(f.get('competencias', [])) < 2:
                return Response(
                    {'error': f"geometry='dtw' compara trajetórias -- estabelecimento '{f.get('facility_uri')}' precisa de pelo menos 2 competências."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    try:
        task = run_population_compare_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            geometry=geometry,
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a comparação PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_causal_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 4:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 4 hospitais."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_causal_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            threshold=data.get('threshold'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise causal PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_anomaly_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 3:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 3 hospitais."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_anomaly_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            contamination=data.get('contamination', 'auto'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a detecção de anomalias PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_risk_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list):
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf})."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_risk_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            weights=data.get('weights'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar o score de risco PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_predict_uncertainty_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 4:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 4 hospitais."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_predict_uncertainty_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            target_feature=data.get('target_feature', 'avg_length_of_stay_days'),
            kernel=data.get('kernel', 'rbf'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a previsão com incerteza PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_classify_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 6 hospitais."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_classify_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            label_feature=data.get('label_feature', 'avg_length_of_stay_days'),
            threshold=data.get('threshold'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar o classificador PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_transitions_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 2:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, uf, competencias: [{ano, mes}, ...]}), com pelo menos 2 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    for f in facility_specs:
        if len(f.get('competencias', [])) < 2:
            return Response(
                {'error': f"Estabelecimento '{f.get('facility_uri')}' precisa de pelo menos 2 competências."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        task = run_population_transitions_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            k=int(data.get('k', 3)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar as transições de fenótipo PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_survival_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, uf, competencias: [{ano, mes}, ...]}), com pelo menos 6 estabelecimentos (amostra mínima para o Cox não ficar sub-determinado)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    for f in facility_specs:
        if len(f.get('competencias', [])) < 2:
            return Response(
                {'error': f"Estabelecimento '{f.get('facility_uri')}' precisa de pelo menos 2 competências."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        task = run_population_survival_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            event_feature=data.get('event_feature', 'mean_age_years'),
            event_threshold=data.get('event_threshold'),
            k=int(data.get('k', 3)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise de sobrevida PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_intervene_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 6 hospitais."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    target_facility_uri = data.get('target_facility_uri')
    if not target_facility_uri or target_facility_uri not in {f.get('facility_uri') for f in facility_specs}:
        return Response(
            {'error': "Campo 'target_facility_uri' é obrigatório e precisa ser um dos estabelecimentos em 'facilities'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    shifts = data.get('shifts')
    if not shifts or not isinstance(shifts, dict):
        return Response(
            {'error': "Campo 'shifts' é obrigatório (dict Feature -> deslocamento em unidade bruta), não pode ser vazio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_intervene_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            target_facility_uri=target_facility_uri,
            shifts=shifts,
            risk_weights=data.get('risk_weights'),
            label_feature=data.get('label_feature', 'avg_length_of_stay_days'),
            threshold=data.get('threshold'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a intervenção contrafactual PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_graph_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    geometry = data.get('geometry', 'euclidean')
    if geometry not in ('euclidean', 'mahalanobis', 'cosine'):
        return Response(
            {'error': "Campo 'geometry' deve ser um de: euclidean, mahalanobis, cosine (DTW não é compatível com grafo de vizinhos)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 6 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_graph_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            geometry=geometry,
            k=int(data.get('k', 5)),
            phenotype_k=int(data.get('phenotype_k', 3)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar o grafo de similaridade PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_factor_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 6 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_factor_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            n_factors=int(data.get('n_factors', 2)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise fatorial PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_topology_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 6 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_topology_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            min_persistence=float(data.get('min_persistence', 0.5)),
            max_dimension=int(data.get('max_dimension', 1)),
            n_cubes=int(data.get('n_cubes', 5)),
            perc_overlap=float(data.get('perc_overlap', 0.3)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise topológica PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_early_warning_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list):
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, uf, competencias: [{ano, mes}, ...]})."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    for f in facility_specs:
        if not f.get('competencias'):
            return Response(
                {'error': f"Estabelecimento '{f.get('facility_uri')}' precisa de pelo menos 1 competência."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        task = run_population_early_warning_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            min_points=int(data.get('min_points', 8)),
            window_size=int(data.get('window_size', 4)),
            n_surrogates=int(data.get('n_surrogates', 200)),
            detrend_method=data.get('detrend_method', 'linear'),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise de alerta precoce PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_gnn_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    geometry = data.get('geometry', 'euclidean')
    if geometry not in ('euclidean', 'mahalanobis', 'cosine'):
        return Response(
            {'error': "Campo 'geometry' deve ser um de: euclidean, mahalanobis, cosine (DTW não é compatível com grafo de vizinhos)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf}), com pelo menos 6 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_gnn_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            geometry=geometry,
            k=int(data.get('k', 5)),
            phenotype_k=int(data.get('phenotype_k', 3)),
            label_fraction=float(data.get('label_fraction', 0.5)),
            hidden_dim=int(data.get('hidden_dim', 16)),
            epochs=int(data.get('epochs', 300)),
            learning_rate=float(data.get('learning_rate', 0.05)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a GNN PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_dynamics_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list) or len(facility_specs) < 6:
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, uf, competencias: [{ano, mes}, ...]}), com pelo menos 6 estabelecimentos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_dynamics_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
            n_worst=int(data.get('n_worst', 5)),
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise de dinâmica PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_per_capita_pipeline(request):
    data = request.data
    facility_specs = data.get('facilities')
    if not facility_specs or not isinstance(facility_specs, list):
        return Response(
            {'error': "Campo 'facilities' é obrigatório (lista de {facility_uri, ano, mes, uf})."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_per_capita_pipeline.delay(
            facility_specs=facility_specs,
            user_id=request.user.id,
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise per capita PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_municipio_pipeline(request):
    data = request.data
    municipio_specs = data.get('municipios')
    if not municipio_specs or not isinstance(municipio_specs, list):
        return Response(
            {'error': "Campo 'municipios' é obrigatório (lista de {cod_ibge, uf, ano, mes})."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    diseases = data.get('diseases', [])

    try:
        task = run_population_municipio_pipeline.delay(
            municipio_specs=municipio_specs,
            diseases=diseases,
            user_id=request.user.id,
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise de município PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_notificacao_pipeline(request):
    data = request.data
    disease_code = data.get('disease_code')
    year_suffixes = data.get('year_suffixes')
    if not disease_code or not year_suffixes or not isinstance(year_suffixes, list):
        return Response(
            {'error': "Campos 'disease_code' e 'year_suffixes' (lista) são obrigatórios."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    limit = data.get('limit', 2000)

    try:
        task = run_population_notificacao_pipeline.delay(
            disease_code=disease_code,
            year_suffixes=year_suffixes,
            limit=limit,
            user_id=request.user.id,
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise de notificação PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasBphoAccess])
def trigger_population_familia_pipeline(request):
    data = request.data
    family_ids = data.get('family_ids')
    sample_size = data.get('sample_size')
    if not family_ids and not sample_size:
        return Response(
            {'error': "Informe 'family_ids' (lista) ou 'sample_size' (inteiro)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        task = run_population_familia_pipeline.delay(
            family_ids=family_ids,
            sample_size=sample_size,
            user_id=request.user.id,
        )
        return Response({'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.exception("Erro ao disparar a análise de família PopulationSpace.")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([HasBphoAccess])
def get_population_space_task_status(request, task_id):
    task_id_str = str(task_id)
    result = AsyncResult(task_id_str)
    response_data = {'task_id': task_id_str, 'status': result.status}

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


class PopulationSpaceTaskListView(generics.ListAPIView):
    serializer_class = PopulationSpaceTaskStatusSerializer
    permission_classes = [HasBphoAccess]

    def get_queryset(self):
        return PopulationSpaceTaskStatus.objects.filter(user=self.request.user).order_by('-created_at')


class PopulationSpaceTaskDetailView(generics.RetrieveAPIView):
    serializer_class = PopulationSpaceTaskStatusSerializer
    permission_classes = [HasBphoAccess]
    lookup_field = 'pk'

    def get_queryset(self):
        return PopulationSpaceTaskStatus.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([HasBphoAccess])
def facility_search(request):
    """
    Busca por prefixo de código CNES contra a BPHO real -- diferente de
    `facility_lookup` (síncrona mas pesada, ~1min: consulta utilização +
    força de trabalho + demografia de UM estabelecimento). A BPHO não
    modela nome/município/UF como propriedade de HealthFacility (só
    `rdf:type` e `:operatedBy`, confirmado contra dado real) -- o único
    campo buscável é o próprio código CNES (sempre 7 dígitos, confirmado
    contra as 448.909 instâncias reais), que forma a URI (`:facility_{cnes}`).

    STRSTARTS sobre a URI é rápido (~20-50ms) quando o prefixo casa com
    MUITOS estabelecimentos reais (a varredura acha os 25 do LIMIT cedo).
    Mas quando o prefixo não casa com NENHUM estabelecimento real -- comum
    enquanto o usuário ainda está digitando um CNES específico -- não há
    índice que permita parar cedo: a consulta varre as 448 mil instâncias
    inteiras e pode passar de 10s (medido). Por isso o timeout aqui é
    propositalmente curto e um timeout é tratado como "sem resultados"
    (200, lista vazia), não como erro -- é o caso normal de digitar um
    prefixo que ainda não corresponde a nada, não uma falha do serviço.

    6s (não 4s) porque medimos um prefixo de 7 dígitos que casa com
    exatamente UM estabelecimento real levando 3.03s -- perto demais de
    4s para sobrar margem contra variação de carga do Virtuoso; um
    prefixo completo que EXISTE é justamente o caso que não pode virar
    falso "sem resultados".
    """
    q = re.sub(r'\D', '', request.query_params.get('q', ''))
    if len(q) < 2:
        return Response({'error': "Parâmetro 'q' precisa de pelo menos 2 dígitos do código CNES."}, status=status.HTTP_400_BAD_REQUEST)
    q = q[:7]

    prefix = f"http://datasus-ontology.local/onto#facility_{q}"
    query = (
        "PREFIX : <http://datasus-ontology.local/onto#>\n"
        "SELECT DISTINCT ?f WHERE { ?f a :HealthFacility . "
        f'FILTER(STRSTARTS(STR(?f), "{prefix}")) }} LIMIT 25'
    )

    try:
        resp = requests.get(
            settings.BPHO_SPARQL_URL,
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=6,
        )
        resp.raise_for_status()
        bindings = resp.json()["results"]["bindings"]
    except requests.exceptions.Timeout:
        return Response({'query': q, 'facilities': [], 'note': "Busca demorou demais (provavelmente sem resultado para esse prefixo)."})
    except Exception as e:
        logger.warning("Falha na busca de estabelecimento por prefixo: %s", e)
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    facility_uris = sorted(b["f"]["value"].rsplit("#", 1)[-1] for b in bindings)
    return Response({'query': q, 'facilities': facility_uris})


@api_view(['GET'])
@permission_classes([HasBphoAccess])
def facility_lookup(request, cnes):
    """
    Busca síncrona de UM estabelecimento -- sem Celery, análogo ao chat
    NL→SPARQL da BPHO (latência parecida, ~1min no pior caso: 3 consultas
    SPARQL + leitura do parquet). `uf` é opcional (sem ele, a composição
    demográfica fica ausente, nunca inventada).
    """
    ano = request.query_params.get('ano')
    mes = request.query_params.get('mes')
    uf = request.query_params.get('uf')
    representation = request.query_params.get('representation', 'hospital')

    if not ano or not mes:
        return Response({'error': "Parâmetros 'ano' e 'mes' são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

    payload = {
        "facility_uri": f"facility_{cnes}",
        "ano": int(ano),
        "mes": int(mes),
        "uf": uf,
        "representation": representation,
    }

    try:
        result = _run_population_cli("facility", payload, timeout=180)
    except Exception as e:
        logger.warning("Falha na busca de estabelecimento PopulationSpace: %s", e)
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(result)
