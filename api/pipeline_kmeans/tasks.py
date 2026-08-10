# === Início do arquivo: api/pipeline_kmeans/tasks.py ===

from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
import os
import json
import logging
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.spatial.distance import euclidean
import warnings
import numpy as np
import re

# Importações para geração de cores da paleta Viridis
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Suprimir avisos específicos do scikit-learn
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.cluster._kmeans")

logger = logging.getLogger(__name__)

# Definir a raiz geral do projeto (ajuste se necessário para seu ambiente de produção)
PROJECT_ROOT_GENERAL = settings.BASE_DIR

# Cores para os Perfis (usadas como fallback se nomes de perfis forem fornecidos sem cores)
CORES_PERFIS_DEFAULT = {
    "Vulnerabilidade Social/Sanitária": "#d73027",
    "Sobrecarga de Doenças Crônicas": "#fc8d59",
    "Atenção Primária Insuficiente": "#4575b4",
    "Atenção Primária Efetiva": "#1a9850",
    "Perfil Desconhecido": "#cccccc"
}

# Dicionário para traduzir nomes técnicos para nomes amigáveis na descrição do arquivo
INDICADORES_FRIENDLY_NAMES = {
    'TMI': 'Taxa de Mortalidade Infantil',
    'COBERTURA_PRENATAL': 'Cobertura de Pré-Natal Adequado (%)',
    'TAXA_MEDICOS': 'Médicos por 1.000 habitantes',
    'PROP_CESAREOS': 'Proporção de Partos Cesáreos (%)',
    'PROP_MAL_DEFINIDAS': 'Proporção de Óbitos por Causas Mal Definidas (%)',
    'DOENCAS_CRONICAS': 'Internações por Condições Sensíveis à Atenção Primária',
    'PROP_MAE_ADOL': 'Proporção de Nascidos Vivos de Mães Adolescentes (%)',
    'TAXA_DETECCAO_HANSENIASE': 'Taxa de Detecção de Hanseníase',
    'TAXA_INTERNACAO_GERAL': 'Taxa de Internação Hospitalar',
    'TAXA_EQUIPES_ESF': 'Cobertura da Estratégia Saúde da Família (%)',
    'TAXA_INCID_DENGUE': 'Taxa de Incidência de Dengue',
    'TAXA_INCID_CHIKUNGUNYA': 'Taxa de Incidência de Chikungunya',
    'TAXA_INCID_ZIKA': 'Taxa de Incidência de Zika',
    'TAXA_INCIDENCIA_TB': 'Taxa de Incidência de Tuberculose',
    'TAXA_ABANDONO_TB': 'Taxa de Abandono de Tratamento de TB (%)',
    'TAXA_CURA_TB': 'Taxa de Cura de Tuberculose (%)',
    'TAXA_MORT_PREM_DCNT': 'Mortalidade Prematura por DCNT',
    'TAXA_MORT_CIRCULATORIO': 'Mortalidade por Doenças Circulatórias',
    'TAXA_MORT_NEOPLASIAS': 'Mortalidade por Neoplasias',
    'TAXA_MORT_RESPIRATORIAS': 'Mortalidade por Doenças Respiratórias',
    'TAXA_MORT_DIABETES': 'Mortalidade por Diabetes',
    'TAXA_MORT_EXTERNAS': 'Mortalidade por Causas Externas',
    'TAXA_MORT_COVID19': 'Mortalidade por COVID-19',
}

def secure_filename(filename):
    """Limpa e sanitiza um nome de arquivo para uso seguro no sistema de arquivos."""
    filename = filename.replace('/', '').replace('\\', '')
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    return filename

def get_viridis_colors(num_colors):
    """Gera uma lista de N cores hexadecimais distintas a partir da paleta Viridis."""
    cmap = plt.get_cmap('viridis')
    points = np.linspace(0, 1, num_colors)
    hex_colors = [mcolors.to_hex(cmap(point)) for point in points]
    return hex_colors

def carregar_arquetipos(archetypes_path: Path, indicator_columns: list) -> tuple[dict, dict]:
    """Carrega arquétipos de um arquivo JSON (formato salvo por
    api/views.py:save_archetype_csv: {profile_column, color_column,
    indicator_columns, rows}). JSON em vez de CSV evita ambiguidade de
    separador/decimal e a necessidade de adivinhar qual coluna é o perfil
    pela posição — os papéis das colunas vêm explícitos no próprio arquivo."""
    if not archetypes_path.exists():
        logger.warning(f"Arquivo de arquétipos não encontrado em: {archetypes_path}")
        return {}, {}
    try:
        with open(archetypes_path, 'r', encoding='utf-8') as f:
            documento = json.load(f)

        perfil_col = documento['profile_column']
        color_col = documento.get('color_column')
        linhas = documento['rows']

        arquetipo_cols_disponiveis = set(linhas[0].keys()) - {perfil_col, color_col} if linhas else set()
        missing_cols = [ind for ind in indicator_columns if ind not in arquetipo_cols_disponiveis]
        if missing_cols:
            logger.error(f"ERRO: Arquivo de arquétipos não contém as colunas esperadas. Faltam: {missing_cols}")
            return {}, {}

        arquetipos, cores_perfis_dict = {}, {}
        for linha in linhas:
            perfil_nome = str(linha[perfil_col])
            arquetipos[perfil_nome] = pd.Series({col: linha[col] for col in indicator_columns})
            cores_perfis_dict[perfil_nome] = str(linha[color_col]) if color_col and color_col in linha else "#cccccc"
        return arquetipos, cores_perfis_dict
    except Exception as e:
        logger.error(f"ERRO ao carregar arquivo de arquétipos: {e}", exc_info=True)
        return {}, {}

def classificar_perfis_por_similaridade(cluster_centers_scaled_df: pd.DataFrame, arquetipos_scaled: dict) -> dict:
    """Classifica cada cluster medindo sua distância euclidiana para arquétipos pré-definidos."""
    mapeamento = {}
    if not arquetipos_scaled:
        return {i: f"Cluster {i}" for i in cluster_centers_scaled_df.index}
    for i, row in cluster_centers_scaled_df.iterrows():
        distancias = {nome: euclidean(row.values, valores) for nome, valores in arquetipos_scaled.items()}
        mapeamento[i] = min(distancias, key=distancias.get) if distancias else f"Cluster {i}"
    return mapeamento

def carregar_e_preparar_dados_indicadores(input_csv_path: Path, indicadores_selecionados: list) -> pd.DataFrame:
    """Carrega e prepara o DataFrame de indicadores para a clusterização."""
    if not input_csv_path.exists():
        return pd.DataFrame()
    try:
        df_painel = pd.read_csv(input_csv_path, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})
        features_para_usar = [ind for ind in indicadores_selecionados if ind in df_painel.columns]
        if not features_para_usar:
             raise ValueError("Nenhum dos indicadores selecionados foi encontrado no arquivo de entrada.")
        cols_essenciais = ['cod_mun_ibge_6', 'ANO', 'UF', 'municipio', 'cod_mun_ibge_7']
        df_painel_filtrado = df_painel[[col for col in list(set(cols_essenciais + features_para_usar)) if col in df_painel.columns]].copy()
        for col in features_para_usar:
            df_painel_filtrado[col] = pd.to_numeric(df_painel_filtrado[col], errors='coerce')
        df_painel_filtrado.dropna(subset=features_para_usar, inplace=True)
        return df_painel_filtrado if not df_painel_filtrado.empty else pd.DataFrame()
    except Exception as e:
        logger.error(f"ERRO ao carregar ou preparar arquivo de indicadores: {e}", exc_info=True)
        return pd.DataFrame()

def executar_kmeans_personalizado(df_painel: pd.DataFrame, num_clusters: int, features_para_cluster: list, output_clustered_data_path: Path, arquetipos: dict = None, cores_perfis: dict = None):
    """Executa o K-Means e salva o resultado no caminho especificado."""
    output_clustered_data_path.parent.mkdir(parents=True, exist_ok=True)
    df_features = df_painel[features_para_cluster]
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df_features)
    if len(df_features) < num_clusters:
        raise ValueError(f"Número de amostras ({len(df_features)}) é menor que o de clusters ({num_clusters}).")
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    df_painel['cluster_num'] = kmeans.fit_predict(scaled_features)
    cluster_centers_scaled = pd.DataFrame(kmeans.cluster_centers_, columns=features_para_cluster)
    if arquetipos:
        arquetipos_scaled = {
            nome: pd.Series(scaler.transform(serie[features_para_cluster].values.reshape(1, -1))[0], index=features_para_cluster)
            for nome, serie in arquetipos.items()
        }
        mapeamento_nomes = classificar_perfis_por_similaridade(cluster_centers_scaled, arquetipos_scaled)
        df_painel['perfil'] = df_painel['cluster_num'].map(mapeamento_nomes)
        df_painel['cor'] = df_painel['perfil'].map(cores_perfis or CORES_PERFIS_DEFAULT)
    else:
        df_painel['perfil'] = "Cluster " + df_painel['cluster_num'].astype(str)
        cluster_colors = get_viridis_colors(num_clusters)
        df_painel['cor'] = df_painel['cluster_num'].apply(lambda x: cluster_colors[x])
    df_painel.to_csv(output_clustered_data_path, index=False, sep=';', encoding='utf-8-sig')
    return output_clustered_data_path

@shared_task(bind=True)
def run_kmeans_pipeline(self, input_file_id, n_clusters, features_for_clustering, archetype_file_id, user_id, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    KMeansTaskStatus = apps.get_model('pipeline_kmeans', 'KMeansTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        input_managed_file = ManagedFile.objects.get(id=input_file_id)
        task_status_entry, _ = KMeansTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={ 'user': user, 'status': 'STARTED', 'input_file': input_managed_file, 'n_clusters': n_clusters, 'features_for_clustering': features_for_clustering, 'message': 'Pipeline K-Means iniciada.' }
        )
        self.update_state(state='PROGRESS', meta={'progress': 5, 'message': 'Carregando dados...'})

        input_csv_path = Path(input_managed_file.file.path)
        df_painel_integrado = carregar_e_preparar_dados_indicadores(input_csv_path, features_for_clustering)
        if df_painel_integrado.empty:
            raise Exception("DataFrame de indicadores vazio ou não pôde ser preparado.")

        arquetipos_carregados, cores_perfis_carregadas = {}, {}
        if archetype_file_id:
            # Resolvido pelo ManagedFile (mesmo padrão de input_managed_file.file.path
            # acima), não por um caminho cru vindo do frontend — evita o bug de
            # receber a URL pública do arquivo (MEDIA_URL) em vez de um caminho
            # de sistema de arquivos válido.
            try:
                archetype_managed_file = ManagedFile.objects.get(id=archetype_file_id)
                archetypes_path_obj = Path(archetype_managed_file.file.path)
                arquetipos_carregados, cores_perfis_carregadas = carregar_arquetipos(archetypes_path_obj, features_for_clustering)
            except ManagedFile.DoesNotExist:
                logger.warning(f"Arquivo de arquétipos ID {archetype_file_id} não encontrado.")

        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Executando K-Means...'})

        if output_filename and output_filename.strip():
            clean_name = output_filename.strip()
            if not clean_name.lower().endswith('.csv'):
                clean_name += '.csv'
            sanitized_filename = secure_filename(clean_name)
            final_filename = sanitized_filename if sanitized_filename else f"kmeans_results_{task_id}.csv"
        else:
            final_filename = f"kmeans_results_{task_id}.csv"

        kmeans_output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "kmeans" / task_id
        final_output_path = kmeans_output_dir / final_filename

        output_clustered_data_path = executar_kmeans_personalizado(
            df_painel=df_painel_integrado, num_clusters=n_clusters, features_para_cluster=features_for_clustering,
            output_clustered_data_path=final_output_path,
            arquetipos=arquetipos_carregados, cores_perfis=cores_perfis_carregadas
        )

        if not output_clustered_data_path or not output_clustered_data_path.exists():
            raise Exception("Execução K-Means não gerou o arquivo de resultados.")

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Registrando resultados...'})

        friendly_indicator_names = [INDICADORES_FRIENDLY_NAMES.get(ind, ind) for ind in features_for_clustering]
        if len(friendly_indicator_names) > 3:
            indicadores_str = ", ".join(sorted(friendly_indicator_names[:3])) + f"... (e mais {len(friendly_indicator_names) - 3})"
        else:
            indicadores_str = ", ".join(sorted(friendly_indicator_names))

        description_text = (
            f"Arquivo de Entrada: {input_managed_file.filename.replace('.csv', '')}. "
            f"Clusters (k): {n_clusters}. "
            f"Indicadores Usados: {indicadores_str}."
        )

        relative_output_path = os.path.relpath(output_clustered_data_path, settings.MEDIA_ROOT)
        output_file_instance, _ = ManagedFile.objects.update_or_create(
            file=relative_output_path,
            defaults={ 'uploader': user, 'filename': output_clustered_data_path.name, 'description': description_text, 'file_type': 'K_MEANS' }
        )
        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Pipeline K-Means concluída. Arquivo: {output_file_instance.filename}"
        task_status_entry.output_file = output_file_instance
        task_status_entry.save()

        return {'status': 'SUCCESS', 'message': 'K-Means concluído!', 'output_file_id': output_file_instance.id}

    except Exception as e:
        logger.exception(f"Erro inesperado na pipeline K-Means {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = f"Falha na pipeline K-Means: {str(e)}"
            task_status_entry.save()
        raise
