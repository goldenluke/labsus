# === Início do arquivo: api/pipeline_indicadores/tasks.py ===

from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
import os
import logging
from pathlib import Path
import importlib.util
import sys
import traceback
from functools import reduce
import re # Importado para expressões regulares (sanitização)

logger = logging.getLogger(__name__)

# --- DEFINIÇÃO DE CAMINHOS ---
ARQUIVO_POP = (
    settings.BASE_DIR
    / "referencia"
    / "populacao"
    / "populacao_estimada_completa_spline.csv"
)
FEATURES_BASE_DIR = Path(__file__).parent / "modules" / "features"
UTILS_DIR_IN_APP = Path(__file__).parent / "modules" / "utils"

if str(UTILS_DIR_IN_APP) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR_IN_APP))

# --- IMPORTAÇÕES LOCAIS AJUSTADAS ---
try:
    from .modules.utils.dataloaders import filtrar_populacao
except ImportError as e:
    logger.error(f"ERRO: Não foi possível importar 'filtrar_populacao' de 'modules.utils.dataloaders'. Verifique o caminho e os '__init__.py's. Erro: {e}")
    raise

def secure_filename(filename):
    """
    Limpa e sanitiza um nome de arquivo para uso seguro no sistema de arquivos.
    Esta função é crucial para prevenir ataques de Path Traversal.
    """
    filename = filename.replace('/', '').replace('\\', '')
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    return filename

# --- Funções auxiliares ---

def discover_feature_functions(features_base_dir: Path) -> dict:
    """
    Descobre e carrega dinamicamente as funções 'processar_dados' de todos os
    módulos de feature no diretório especificado.
    """
    feature_functions = {}
    logger.info(f"Procurando por módulos de feature em: {features_base_dir}")
    if not features_base_dir.is_dir():
        logger.error(f"DIRETÓRIO DE FEATURES NÃO ENCONTRATO: {features_base_dir}.")
        return {}
    found_files = list(features_base_dir.glob('*.py'))
    for f in found_files:
        if f.name.startswith(('__init__', '.')):
            continue
        module_name = f.stem
        module_path_name = f"api.pipeline_indicadores.modules.features.{module_name}"
        spec = importlib.util.spec_from_file_location(module_path_name, f)
        if spec is None:
            continue
        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_path_name] = module
            spec.loader.exec_module(module)
            if hasattr(module, 'processar_dados'):
                feature_functions[module_name] = getattr(module, 'processar_dados')
                logger.info(f" -> SUCESSO: Módulo de feature '{module_name}' carregado.")
        except Exception as e:
            logger.error(f"ERRO GERAL ao carregar '{f.name}': {e}", exc_info=True)
    return feature_functions

# --- DICIONÁRIOS DE MAPEAMENTO ---

INDICADOR_TO_FEATURE_MODULE = {
    'TAXA_INCIDENCIA_TB': 'indicadores_tuberculose',
    'TAXA_ABANDONO_TB': 'indicadores_tuberculose',
    'TAXA_CURA_TB': 'indicadores_tuberculose',
    'TAXA_MORT_PREM_DCNT': 'mortalidade_prematura_dcnt',
    'PROP_MAL_DEFINIDAS': 'causas_mal_definidas',
    'TAXA_EQUIPES_ESF': 'equipes_esf_taxa',
    'TMI': 'mortalidade_infantil',
    'TAXA_INCID_CHIKUNGUNYA': 'incidencia_arboviroses',
    'TAXA_INCID_ZIKA': 'incidencia_arboviroses',
    'TAXA_INCID_DENGUE': 'incidencia_arboviroses',
    'PROP_CESAREOS': 'partos_cesareos',
    'PROP_MAE_ADOL': 'maes_adolescentes',
    'TAXA_INTERNACAO_GERAL': 'internacoes_gerais',
    'DOENCAS_CRONICAS': 'doencas_cronicas',
    'ICSAP': 'icsap',
    'ICSAP_PROP': 'icsap',
    'IND_CARGA_HOSPITALAR_ESF': 'carga_hospitalar_esf',
    'IND_ADEQUACAO_UTI_NEONATAL': 'adequacao_uti_neonatal',
    'TAXA_RESOLUTIVIDADE_AMBULATORIAL': 'resolutividade_ambulatorial',
    'TAXA_COBERTURA_CITOPATOLOGICO': 'citopatologico_colo_utero',
    'TAXA_COBERTURA_MAMOGRAFIA': 'mamografia_rastreamento',
    'TAXA_MEDICOS': 'medicos_por_mil',
    'TAXA_DETECCAO_HANSENIASE': 'hanseniase',
    'COBERTURA_PRENATAL': 'pre_natal',
    'TAXA_MORT_CIRCULATORIO': 'mortalidade_causas_especificas',
    'TAXA_MORT_NEOPLASIAS': 'mortalidade_causas_especificas',
    'TAXA_MORT_RESPIRATORIAS': 'mortalidade_causas_especificas',
    'TAXA_MORT_DIABETES': 'mortalidade_causas_especificas',
    'TAXA_MORT_EXTERNAS': 'mortalidade_causas_especificas',
    'TAXA_MORT_COVID19': 'mortalidade_causas_especificas',

    # --- Novos indicadores de agravos do SINAN ---
    'TAXA_INCIDENCIA_CHAGAS': 'chagas',
    'TAXA_INCIDENCIA_ESQU': 'esquistossomose',
    'TAXA_INCIDENCIA_MALARIA': 'malaria',
    'TAXA_INCIDENCIA_LEIV': 'leishmaniose_visceral',
    'TAXA_INCIDENCIA_LTAN': 'leishmaniose_tegumentar',
    'TAXA_INCIDENCIA_HEPATITES': 'hepatites_virais',
    'TAXA_INCIDENCIA_SIFA': 'sifilis_adquirida',
    'TAXA_INCIDENCIA_SIFG': 'sifilis_gestante',
    'TAXA_INCIDENCIA_SIFC': 'sifilis_congenita',
    'TAXA_CONF_ANIMAIS_P': 'acidentes_animais_peconhentos',
    'TAXA_RAIVA_HUMANA': 'raiva_humana',
    'TAXA_INCIDENCIA_LEPTO': 'leptospirose',
    'TAXA_INCIDENCIA_MENI': 'meningite',
    'TAXA_INCIDENCIA_DIFT': 'difteria',
    'TAXA_INCIDENCIA_COQU': 'coqueluche',
    'TAXA_ACIDENTE_TRABALHO': 'acidente_trabalho_grave',
    'TAXA_INTOX_EXOGENA': 'intoxicacao_exogena',
    'TAXA_NOTIFICACAO_VIOLENCIA': 'violencia_interpessoal',
    'TAXA_INCIDENCIA_FTIF': 'febre_tifoide',
    'TAXA_INCIDENCIA_HANTAVIROSE': 'hantavirose',
    'TAXA_INCIDENCIA_SARAMPO': 'doencas_exantematicas',
    'TAXA_INCIDENCIA_RUBEOLA': 'doencas_exantematicas',
    'TAXA_INCIDENCIA_FMAC': 'febre_maculosa',
    'TAXA_NOTIFICACAO_DERM': 'dermatoses_ocupacionais',
    'TAXA_NOTIFICACAO_CANCER_TRAB': 'cancer_trabalho',
    'TAXA_INCIDENCIA_BOTULISMO': 'botulismo',
    'TAXA_NOTIFICACAO_ACBI': 'acidente_material_biologico',

    # --- Mais indicadores de agravos do SINAN ---
    'TAXA_INCIDENCIA_COLERA': 'colera',
    'TAXA_NOTIFICACAO_LERDORT': 'ler_dort',
    'TAXA_NOTIFICACAO_TRANSTORNO_MENTAL_TRAB': 'transtorno_mental_trabalho',
    'TAXA_NOTIFICACAO_PAIR': 'pair_trabalho',
    'TAXA_INCIDENCIA_PESTE': 'peste',
    'TAXA_NOTIFICACAO_PARALISIA_FLACIDA': 'paralisia_flacida_aguda',
    'TAXA_NOTIFICACAO_PNEUMOCONIOSE': 'pneumoconiose_trabalho',
    'TAXA_INCIDENCIA_SRC': 'sindrome_rubeola_congenita',
    'TAXA_INCIDENCIA_TETANO_ACIDENTAL': 'tetano_acidental',
    'TAXA_INCIDENCIA_TETANO_NEONATAL': 'tetano_neonatal',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_CONGENITA': 'toxoplasmose_congenita',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_GESTACIONAL': 'toxoplasmose_gestacional',

    # --- Índices compostos (agregações diretas, sem linkage nem modelo) ---
    'IND_CAPACIDADE_ASSISTENCIAL': 'capacidade_assistencial',
    'IND_COMPLEXIDADE_HOSPITALAR': 'complexidade_hospitalar',
    'SHANNON_DIVERSIDADE_OBITOS': 'diversidade_epidemiologica',
    'SHANNON_DIVERSIDADE_INTERNACOES': 'diversidade_epidemiologica',
    'IND_ESPECIALIZACAO_HOSPITALAR': 'especializacao_hospitalar',
    'IND_PRESSAO_LEITOS': 'pressao_hospitalar',
    'IND_RESOLUTIVIDADE': 'resolutividade_hospitalar',
    'IND_COBERTURA_ASSISTENCIAL': 'cobertura_assistencial',
    'SHANNON_DIVERSIDADE_ASSISTENCIAL': 'diversidade_assistencial',
    'TMH_HOSPITALAR_PADRONIZADA': 'mortalidade_hospitalar_ajustada',
    'IQI_QUALIDADE_INFORMACAO': 'qualidade_informacao',
    'TAXA_MORTALIDADE_GERAL': 'mortalidade_geral',
}

INDICADORES_FRIENDLY_NAMES = {
    'TMI': 'Taxa de Mortalidade Infantil',
    'COBERTURA_PRENATAL': 'Cobertura de Pré-Natal Adequado (%)',
    'TAXA_MEDICOS': 'Médicos por 1.000 habitantes',
    'PROP_CESAREOS': 'Proporção de Partos Cesáreos (%)',
    'PROP_MAL_DEFINIDAS': 'Proporção de Óbitos por Causas Mal Definidas (%)',
    'DOENCAS_CRONICAS': 'Internações por Doenças Crônicas Selecionadas (Hipertensão/Diabetes/Asma, por 10 mil hab.)',
    'ICSAP': 'Taxa de Internações por Condições Sensíveis à Atenção Primária (ICSAP, por 10 mil hab.)',
    'ICSAP_PROP': 'Proporção de Internações por Condições Sensíveis à Atenção Primária (%)',
    'IND_CARGA_HOSPITALAR_ESF': 'Índice de Carga Hospitalar por Equipe ESF (SIH+CNES: internações/equipe)',
    'IND_ADEQUACAO_UTI_NEONATAL': 'Índice de Adequação de UTI Neonatal (SINASC+CNES: nascidos de baixo peso/leito)',
    'TAXA_RESOLUTIVIDADE_AMBULATORIAL': 'Taxa de Resolutividade Ambulatorial (SIA+SIH: procedimentos/internação ICSAP)',
    'TAXA_COBERTURA_CITOPATOLOGICO': 'Cobertura de Exame Citopatológico do Colo do Útero (SIA, rastreamento, por 1.000 hab.)',
    'TAXA_COBERTURA_MAMOGRAFIA': 'Cobertura de Mamografia de Rastreamento (SIA, por 1.000 hab.)',
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

    # --- Novos indicadores de agravos do SINAN ---
    'TAXA_INCIDENCIA_CHAGAS': 'Taxa de Incidência de Doença de Chagas Aguda (por 100 mil hab.)',
    'TAXA_INCIDENCIA_ESQU': 'Taxa de Incidência de Esquistossomose (por 100 mil hab.)',
    'TAXA_INCIDENCIA_MALARIA': 'Taxa de Incidência de Malária (por 100 mil hab.)',
    'TAXA_INCIDENCIA_LEIV': 'Taxa de Incidência de Leishmaniose Visceral (por 100 mil hab.)',
    'TAXA_INCIDENCIA_LTAN': 'Taxa de Incidência de Leishmaniose Tegumentar (por 100 mil hab.)',
    'TAXA_INCIDENCIA_HEPATITES': 'Taxa de Incidência de Hepatites Virais (por 100 mil hab.)',
    'TAXA_INCIDENCIA_SIFA': 'Taxa de Incidência de Sífilis Adquirida (por 100 mil hab.)',
    'TAXA_INCIDENCIA_SIFG': 'Taxa de Incidência de Sífilis em Gestante (por 100 mil hab.)',
    'TAXA_INCIDENCIA_SIFC': 'Taxa de Incidência de Sífilis Congênita (por 100 mil hab.)',
    'TAXA_CONF_ANIMAIS_P': 'Taxa de Acidentes por Animais Peçonhentos (por 100 mil hab.)',
    'TAXA_RAIVA_HUMANA': 'Taxa de Raiva Humana (por 100 mil hab.)',
    'TAXA_INCIDENCIA_LEPTO': 'Taxa de Incidência de Leptospirose (por 100 mil hab.)',
    'TAXA_INCIDENCIA_MENI': 'Taxa de Incidência de Meningite (por 100 mil hab.)',
    'TAXA_INCIDENCIA_DIFT': 'Taxa de Incidência de Difteria (por 100 mil hab.)',
    'TAXA_INCIDENCIA_COQU': 'Taxa de Incidência de Coqueluche (por 100 mil hab.)',
    'TAXA_ACIDENTE_TRABALHO': 'Taxa de Acidente de Trabalho Grave (por 100 mil hab.)',
    'TAXA_INTOX_EXOGENA': 'Taxa de Intoxicação Exógena (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_VIOLENCIA': 'Taxa de Notificação de Violência Interpessoal/Autoprovocada (por 100 mil hab.)',
    'TAXA_INCIDENCIA_FTIF': 'Taxa de Incidência de Febre Tifóide (por 100 mil hab.)',
    'TAXA_INCIDENCIA_HANTAVIROSE': 'Taxa de Incidência de Hantavirose (por 100 mil hab.)',
    'TAXA_INCIDENCIA_SARAMPO': 'Taxa de Incidência de Sarampo (por 100 mil hab.)',
    'TAXA_INCIDENCIA_RUBEOLA': 'Taxa de Incidência de Rubéola (por 100 mil hab.)',
    'TAXA_INCIDENCIA_FMAC': 'Taxa de Incidência de Febre Maculosa (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_DERM': 'Taxa de Notificação de Dermatoses Ocupacionais (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_CANCER_TRAB': 'Taxa de Notificação de Câncer Relacionado ao Trabalho (por 100 mil hab.)',
    'TAXA_INCIDENCIA_BOTULISMO': 'Taxa de Incidência de Botulismo (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_ACBI': 'Taxa de Notificação de Acidente c/ Material Biológico (por 100 mil hab.)',

    # --- Mais indicadores de agravos do SINAN ---
    'TAXA_INCIDENCIA_COLERA': 'Taxa de Incidência de Cólera (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_LERDORT': 'Taxa de Notificação de LER/DORT Relacionado ao Trabalho (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_TRANSTORNO_MENTAL_TRAB': 'Taxa de Notificação de Transtorno Mental Relacionado ao Trabalho (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_PAIR': 'Taxa de Notificação de Perda Auditiva Induzida por Ruído (Trabalho) (por 100 mil hab.)',
    'TAXA_INCIDENCIA_PESTE': 'Taxa de Incidência de Peste (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_PARALISIA_FLACIDA': 'Taxa de Notificação de Paralisia Flácida Aguda (por 100 mil hab.)',
    'TAXA_NOTIFICACAO_PNEUMOCONIOSE': 'Taxa de Notificação de Pneumoconiose Relacionada ao Trabalho (por 100 mil hab.)',
    'TAXA_INCIDENCIA_SRC': 'Taxa de Incidência de Síndrome da Rubéola Congênita (por 100 mil hab.)',
    'TAXA_INCIDENCIA_TETANO_ACIDENTAL': 'Taxa de Incidência de Tétano Acidental (por 100 mil hab.)',
    'TAXA_INCIDENCIA_TETANO_NEONATAL': 'Taxa de Incidência de Tétano Neonatal (por 100 mil hab.)',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_CONGENITA': 'Taxa de Incidência de Toxoplasmose Congênita (por 100 mil hab.)',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_GESTACIONAL': 'Taxa de Incidência de Toxoplasmose Gestacional (por 100 mil hab.)',

    # --- Índices compostos (agregações diretas, sem linkage nem modelo) ---
    'IND_CAPACIDADE_ASSISTENCIAL': 'Índice de Capacidade Assistencial (CNES: leitos/médicos/enfermeiros/eSF)',
    'IND_COMPLEXIDADE_HOSPITALAR': 'Índice de Complexidade Hospitalar (SIH: procedimentos/CIDs distintos)',
    'SHANNON_DIVERSIDADE_OBITOS': 'Diversidade Epidemiológica — Óbitos (Shannon, SIM)',
    'SHANNON_DIVERSIDADE_INTERNACOES': 'Diversidade Epidemiológica — Internações (Shannon, SIH)',
    'IND_ESPECIALIZACAO_HOSPITALAR': 'Índice de Especialização Hospitalar (% no capítulo CID principal)',
    'IND_PRESSAO_LEITOS': 'Índice de Pressão Hospitalar (internações por leito)',
    'IND_RESOLUTIVIDADE': 'Índice de Resolutividade Hospitalar (% alta sem óbito)',
    'IND_COBERTURA_ASSISTENCIAL': 'Índice de Cobertura Assistencial (CNES: UBS/hospitais/eSF por habitante)',
    'SHANNON_DIVERSIDADE_ASSISTENCIAL': 'Índice de Diversidade Assistencial (Shannon dos tipos de estabelecimento)',
    'TMH_HOSPITALAR_PADRONIZADA': 'Mortalidade Hospitalar Ajustada por Idade (SIH, padronização direta)',
    'IQI_QUALIDADE_INFORMACAO': 'Índice de Qualidade da Informação (SIM+SINASC: completude de idade/sexo/raça/escolaridade)',
    'TAXA_MORTALIDADE_GERAL': 'Taxa de Mortalidade Geral (por 1.000 hab., SIM)',
}

# --- Tasks Celery ---

@shared_task
def run_pipeline_indicadores_task(ufs, anos, arboviroses, mortalidade, indicadores):
    logger.info(f"Executando pipeline de indicadores: ufs={ufs}, anos={anos}")
    return "Pipeline de indicadores executado com sucesso"


@shared_task(bind=True)
def run_integracao_pipeline(self, ufs, anos, arboviroses, mortalidade, indicadores=None, output_csv_filename=None, pop_csv_path=None, user_id=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    IntegracaoTaskStatus = apps.get_model('pipeline_indicadores', 'IntegracaoTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    if pop_csv_path is None:
        ARQUIVO_POP = settings.BASE_DIR / "referencia" / "populacao" / "populacao_estimada_completa_spline.csv"
    else:
        ARQUIVO_POP = Path(pop_csv_path)

    if output_csv_filename and output_csv_filename.strip():
        clean_name = output_csv_filename.strip()
        if not clean_name.lower().endswith('.csv'):
            clean_name += '.csv'
        sanitized_filename = secure_filename(clean_name)
        final_filename = sanitized_filename if sanitized_filename else f"indicadores_integrados_{task_id}.csv"
    else:
        final_filename = f"indicadores_integrados_{task_id}.csv"

    ARQUIVO_INDICADORES_INTEGRADOS = Path(settings.MEDIA_ROOT) / "processed_data" / "integracao" / final_filename

    try:
        task_status_entry, created = IntegracaoTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={'user': user, 'status': 'STARTED', 'input_files': [], 'message': 'Pipeline de integração iniciada.'}
        )
        if not created:
            task_status_entry.status = 'STARTED'
            task_status_entry.message = 'Pipeline de integração reiniciada.'
            task_status_entry.save()

        if not ARQUIVO_POP.exists():
            raise Exception(f"Arquivo de população não encontrado em '{ARQUIVO_POP}'.")

        funcoes_disponiveis = discover_feature_functions(FEATURES_BASE_DIR)
        if not funcoes_disponiveis:
            raise Exception(f"Nenhuma função de feature encontrada em '{FEATURES_BASE_DIR}'.")

        logger.info(f"🚀 INICIANDO O PIPELINE DE INTEGRAÇÃO (Task: {task_id}) 🚀")

        indicadores_a_processar_modulos = []
        if indicadores and isinstance(indicadores, list) and len(indicadores) > 0:
            for ind_frontend_name in indicadores:
                module_name = INDICADOR_TO_FEATURE_MODULE.get(ind_frontend_name)
                if module_name and module_name in funcoes_disponiveis:
                    indicadores_a_processar_modulos.append(module_name)
                else:
                    logger.warning(f"Aviso: Indicador '{ind_frontend_name}' não tem mapeamento ou módulo válido. Pulando.")
            if not indicadores_a_processar_modulos:
                raise Exception("Nenhum indicador selecionado corresponde a um módulo válido.")
        else:
            indicadores_a_processar_modulos = list(funcoes_disponiveis.keys())

        self.update_state(state='PROGRESS', meta={'progress': 5, 'message': 'Criando DataFrame base...'})
        df_base_list = [filtrar_populacao(ARQUIVO_POP, u, a).reset_index() for u in ufs for a in anos if filtrar_populacao(ARQUIVO_POP, u, a) is not None]
        if not df_base_list:
            raise Exception("Não foi possível carregar dados de população.")
        df_final = pd.concat(df_base_list, ignore_index=True)
        chaves_base = ['cod_mun_ibge_6', 'ANO', 'UF', 'municipio', 'cod_mun_ibge_7', 'populacao']
        df_final = df_final[[c for c in chaves_base if c in df_final.columns]].copy()

        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Calculando indicadores...'})

        modulos_unicos_a_processar = sorted(list(set(indicadores_a_processar_modulos)))
        total_features = len(modulos_unicos_a_processar)
        initial_merge_df_final = df_final.copy()

        for i, nome_indicador_modulo in enumerate(modulos_unicos_a_processar):
            self.update_state(state='PROGRESS', meta={'progress': 20 + int((i / total_features) * 60), 'message': f'Processando: {nome_indicador_modulo}'})
            funcao_a_chamar = funcoes_disponiveis.get(nome_indicador_modulo)
            if funcao_a_chamar:
                try:
                    params = {"ufs": ufs, "anos": anos, "arquivo_populacao": ARQUIVO_POP, "doencas": arboviroses, "causa_grupo": mortalidade, "meses": None}
                    df_feature = funcao_a_chamar(**params)
                    if df_feature is not None and not df_feature.empty:
                        chaves_juncao = ['cod_mun_ibge_6', 'ANO', 'UF']
                        cols_indicadores = [c for c in df_feature.columns if c.isupper() and c not in chaves_juncao]
                        if cols_indicadores:
                            df_feature_limpo = df_feature[chaves_juncao + cols_indicadores].drop_duplicates(subset=chaves_juncao)
                            initial_merge_df_final = pd.merge(initial_merge_df_final, df_feature_limpo, on=chaves_juncao, how='left')
                except Exception as e:
                    logger.error(f"Erro ao processar '{nome_indicador_modulo}': {e}", exc_info=True)

        df_final = initial_merge_df_final.copy()
        if df_final.empty:
            raise Exception("Nenhum dado foi mesclado com sucesso.")

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Finalizando...'})
        cols_indicadores_final = [c for c in df_final.columns if c.isupper() and c not in ['UF', 'ANO']]
        df_final[cols_indicadores_final] = df_final[cols_indicadores_final].fillna(0)
        ARQUIVO_INDICADORES_INTEGRADOS.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_csv(ARQUIVO_INDICADORES_INTEGRADOS, sep=';', encoding='utf-8-sig', index=False)

        ufs_str = ", ".join(sorted(ufs))
        anos_str = ", ".join(sorted(map(str, anos)))

        if indicadores:
            friendly_names = sorted([INDICADORES_FRIENDLY_NAMES.get(ind, ind) for ind in indicadores])
            if len(friendly_names) > 5:
                indicadores_str = ", ".join(friendly_names[:5]) + f"... (e mais {len(friendly_names) - 5})"
            else:
                indicadores_str = ", ".join(friendly_names)
        else:
            indicadores_str = "Todos os disponíveis"

        description_text = (f"UFs: {ufs_str}. Anos: {anos_str}. Indicadores: {indicadores_str}.")

        output_file_instance, _ = ManagedFile.objects.update_or_create(
            file=os.path.relpath(ARQUIVO_INDICADORES_INTEGRADOS, settings.MEDIA_ROOT),
            defaults={'uploader': user, 'filename': ARQUIVO_INDICADORES_INTEGRADOS.name, 'description': description_text, 'file_type': 'INDICATORS'}
        )
        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Pipeline concluída. Arquivo: {output_file_instance.filename}"
        task_status_entry.output_file = output_file_instance
        task_status_entry.save()

        logger.info("🎉 FLUXO DE INTEGRAÇÃO CONCLUÍDO! 🎉")
        return {'status': 'SUCCESS', 'message': 'Dados consolidados!', 'output_file_id': output_file_instance.id}

    except Exception as e:
        logger.exception(f"Erro inesperado na pipeline de integração {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = f"Falha na pipeline: {e}"
            task_status_entry.save()
        raise
