# === Início do arquivo: api/views.py ===

# Imports do Django e Rest Framework
import logging
import pandas as pd
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
# ⭐ 1. ADICIONE 'filters' À IMPORTAÇÃO DO REST_FRAMEWORK ⭐
from rest_framework import status, generics, permissions, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.db import transaction
from rest_framework.parsers import JSONParser
import numpy as np
import json
import os

# Imports de autenticação
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# Imports locais do seu aplicativo 'api'
from .models import ManagedFile, FileType
from .serializers import ManagedFileSerializer, ArchetypeDataSerializer
from .cache import GEOJSON_CACHE

# Inicializa o logger
logger = logging.getLogger(__name__)


# Classe de Paginação Padrão para a API
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 9 # Número de itens por página (ajustado para corresponder ao frontend)
    page_size_query_param = 'page_size' # Permite ao cliente definir o tamanho da página
    max_page_size = 100 # Limite máximo de itens por página


### **Views Base e de Autenticação**

class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://labsus.ddns.net:3000" # URL do seu frontend
    client_class = OAuth2Client


@ensure_csrf_cookie
def set_csrf_cookie(request):
    """
    View simples para definir o cookie CSRF no cliente, facilitando
    interações a partir de frontends SPA (Single Page Application).
    """
    return JsonResponse({'detail': 'CSRF cookie set'})


### **Views para Gerenciamento de Ficheiros do Utilizador (ManagedFile)**

class ManagedFileListCreateAPIView(generics.ListCreateAPIView):
    """
    Endpoint para um utilizador listar os seus ficheiros ou fazer upload de um novo.
    GET: Retorna a lista de ficheiros do utilizador logado, com suporte a paginação e busca.
    POST: Permite o upload de um novo ficheiro CSV.
    """
    serializer_class = ManagedFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    # ⭐ 2. HABILITA OS FILTROS DE BUSCA E ORDENAÇÃO DO DRF ⭐
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # ⭐ 3. DEFINE OS CAMPOS ONDE A BUSCA DEVE PROCURAR ⭐
    search_fields = ['filename', 'description', 'uploader__username']

    # ⭐ 4. DEFINE OS CAMPOS QUE PODEM SER USADOS PARA ORDENAÇÃO ⭐
    ordering_fields = ['filename', 'uploaded_at', 'file_type']

    # Define uma ordenação padrão (opcional, pode ser feito no get_queryset também)
    ordering = ['-uploaded_at']


    def get_queryset(self):
        # --- INÍCIO DO CÓDIGO DE DEBUG ---
        print("\n--- DEBUG: get_queryset para ManagedFileListCreateAPIView ---")
        user_logado = self.request.user
        print(f"[1] Usuário logado que está fazendo a requisição: '{user_logado.username}' (ID: {user_logado.id})")

        # Busca inicial, apenas pelo usuário
        queryset = ManagedFile.objects.filter(uploader=user_logado).exclude(file_type=FileType.CHART_DATA)
        print(f"[2] Encontrados {queryset.count()} arquivo(s) no total para este usuário.")

        # Lógica de filtro por file_type
        file_type = self.request.query_params.get('file_type', None)
        print(f"[3] Frontend solicitou o filtro file_type = '{file_type}'")

        if file_type and file_type != 'ALL':
            if file_type in FileType.values:
                queryset = queryset.filter(file_type=file_type)
                print(f"[4] Após aplicar o filtro, restaram {queryset.count()} arquivo(s).")
            else:
                print(f"[!] AVISO: O file_type '{file_type}' não é uma opção válida.")
        else:
            print("[4] Nenhum filtro de file_type foi aplicado.")

        print("--- FIM DO DEBUG ---\n")
        # --- FIM DO CÓDIGO DE DEBUG ---

        return queryset


class ManagedFileDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Endpoint para um usuário obter, atualizar ou excluir
    um arquivo específico pelo seu ID.
    GET: Retorna os detalhes de um arquivo.
    PUT/PATCH: Atualiza os detalhes de um arquivo (ex: nome, descrição).
    DELETE: Exclui um arquivo.
    """
    serializer_class = ManagedFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Garante que o usuário só possa interagir com seus próprios arquivos.
        return ManagedFile.objects.filter(uploader=self.request.user)

    def perform_destroy(self, instance):
        """
        Sobrescreve o método de exclusão para também deletar o arquivo físico.
        """
        # Primeiro, deleta o arquivo físico do sistema de arquivos
        if instance.file and hasattr(instance.file, 'path'):
            file_path = Path(instance.file.path)
            if file_path.exists():
                try:
                    os.remove(file_path)
                    logger.info(f"Arquivo físico '{file_path}' deletado com sucesso.")
                except OSError as e:
                    logger.error(f"Erro ao deletar o arquivo físico '{file_path}': {e}")

        # Depois, chama o método padrão para deletar o registro do banco de dados
        instance.delete()


class ManagedFileDataAPIView(APIView):
    """
    Endpoint para obter os dados em formato JSON de um ficheiro CSV específico
    que foi enviado pelo utilizador.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            managed_file = ManagedFile.objects.get(pk=pk, uploader=request.user)
        except ManagedFile.DoesNotExist:
            return Response({"error": "Arquivo não encontrado ou permissão negada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_path = Path(managed_file.file.path)
            if not file_path.exists():
                logger.error(f"Arquivo físico não encontrado para ManagedFile ID {managed_file.id}: {file_path}")
                return Response({"error": "Arquivo físico não encontrado no servidor."}, status=status.HTTP_404_NOT_FOUND)

            dtype_mapping = { 'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str }
            df = pd.read_csv(file_path, sep=';', engine='python', dtype=dtype_mapping, na_values=[''])
            df = df.replace([np.inf, -np.inf], np.nan)
            data_json = json.loads(df.to_json(orient='records', date_format='iso'))
            return Response(data_json, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Erro ao processar o ManagedFile ID {managed_file.id}.")
            return Response({"error": f"Erro ao processar o ficheiro: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### **View para Servir os Mapas (GeoJSON)**

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_geojson_for_uf(request, uf):
    """
    Endpoint da API para fornecer o arquivo GeoJSON para uma UF específica
    a partir do cache pré-carregado na memória do servidor.
    """
    uf_upper = uf.upper()
    geojson_data = GEOJSON_CACHE.get(uf_upper)
    if geojson_data:
        return JsonResponse(geojson_data, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'error': f'GeoJSON para a UF "{uf_upper}" não encontrado no cache.'}, status=status.HTTP_404_NOT_FOUND)


### **View para Salvar Arquétipos**

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([JSONParser])
def save_archetype_csv(request):
    """
    Endpoint para receber dados de arquétipos em JSON e salvá-los como JSON
    (não CSV — evita ambiguidade de separador/decimal e a necessidade de
    adivinhar qual coluna é o perfil por posição; ver carregar_arquetipos()
    em api/pipeline_kmeans/tasks.py) registrando como um ManagedFile do tipo
    'ARCHETYPE'.
    """
    serializer = ArchetypeDataSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"Erro de validação ao salvar arquétipos: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    filename_base = validated_data['filename']
    data_rows = validated_data['data_rows']
    indicator_columns = validated_data['indicator_columns']
    profile_column_name = validated_data['profile_column_name']
    color_column_name = validated_data.get('color_column_name', None)

    archetype_document = {
        'profile_column': profile_column_name,
        'color_column': color_column_name,
        'indicator_columns': indicator_columns,
        'rows': data_rows,
    }

    timestamp = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{filename_base.replace('.csv', '').replace('.json', '')}_{timestamp}.json"

    ARCHETYPES_UPLOAD_DIR = Path(settings.MEDIA_ROOT) / "uploads" / "archetypes"
    ARCHETYPES_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_full_path = ARCHETYPES_UPLOAD_DIR / unique_filename

    try:
        with open(file_full_path, 'w', encoding='utf-8') as f:
            json.dump(archetype_document, f, ensure_ascii=False, indent=2)
        logger.info(f"Arquivo de arquétipos salvo em: {file_full_path}")

        with transaction.atomic():
            relative_path = os.path.join("uploads", "archetypes", unique_filename)
            managed_file = ManagedFile.objects.create(
                uploader=request.user,
                file=relative_path,
                filename=unique_filename,
                description=f"Arquivo de arquétipos para K-Means: {filename_base}",
                file_type=FileType.ARCHETYPE
            )
            managed_file_serializer = ManagedFileSerializer(managed_file)
            return Response(managed_file_serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Erro ao salvar arquivo de arquétipos ou registrar ManagedFile: {e}", exc_info=True)
        if file_full_path.exists():
            file_full_path.unlink()
        return Response({'error': f'Falha ao criar arquivo de arquétipos: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# === Fim do arquivo: api/views.py ===
