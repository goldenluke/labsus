# === Início do arquivo: api/pipeline_predicao_internacoes/tasks.py (CORRIGIDO) ===

from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
import numpy as np
from prophet import Prophet
from pathlib import Path
import logging
import os
import sys
import re # Importado para sanitização de nome de arquivo

from pysus.online_data.SIH import SIH
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="prophet")

logger = logging.getLogger(__name__)

# Definir a raiz geral do projeto
PROJECT_ROOT_GENERAL = Path(settings.BASE_DIR).parent.parent

def secure_filename(filename):
    """
    Limpa e sanitiza um nome de arquivo para uso seguro no sistema de arquivos.
    """
    filename = filename.replace('/', '').replace('\\', '')
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    return filename

# --- Funções do script original, adaptadas para logging e retorno ---

def carregar_dados_sih(ufs: list, anos: list, cid_codes: list, task_instance=None):
    """
    Carrega e processa dados do SIH para um período e UFs específicos.
    """
    # ... (código desta função permanece inalterado)
    cid_str_log = ", ".join(cid_codes)
    message = f"Iniciando carregamento de dados do SIH para os códigos CID '{cid_str_log}'..."
    if task_instance: task_instance.update_state(state='PROGRESS', meta={'progress': 10, 'message': message})
    try:
        sih_db = SIH()
        sih_db.load()
        dfs_sih = []
        for ano in anos:
            for uf in ufs:
                files = sih_db.get_files(group='RD', uf=uf, year=ano)
                if files:
                    parquet_set = sih_db.download(files)
                    if isinstance(parquet_set, list):
                        dfs_sih.extend([p.to_dataframe() for p in parquet_set])
                    elif hasattr(parquet_set, "to_dataframe"):
                        dfs_sih.append(parquet_set.to_dataframe())

        if not dfs_sih: return pd.DataFrame()

        df_sih_full = pd.concat(dfs_sih, ignore_index=True)
        prefixes = [code for code in cid_codes if len(code) == 1]
        full_codes = [code for code in cid_codes if len(code) >= 3]

        mask_prefix = df_sih_full['DIAG_PRINC'].astype(str).str.startswith(tuple(prefixes)) if prefixes else pd.Series(False, index=df_sih_full.index)
        mask_full = df_sih_full['DIAG_PRINC'].isin(full_codes) if full_codes else pd.Series(False, index=df_sih_full.index)

        df_filtrado_causa = df_sih_full[mask_prefix | mask_full].copy()
        df_filtrado_causa['UF_RES'] = df_filtrado_causa['MUNIC_RES'].str[:2]
        mapa_uf_cod = {'11':'RO', '12':'AC', '13':'AM', '14':'RR', '15':'PA', '16':'AP', '17':'TO', '21':'MA', '22':'PI', '23':'CE', '24':'RN', '25':'PB', '26':'PE', '27':'AL', '28':'SE', '29':'BA', '31':'MG', '32':'ES', '33':'RJ', '35':'SP', '41':'PR', '42':'SC', '43':'RS', '50':'MS', '51':'MT', '52':'GO', '53':'DF'}
        df_filtrado_causa['UF_RES'] = df_filtrado_causa['UF_RES'].map(mapa_uf_cod)
        df_filtrado_uf = df_filtrado_causa[df_filtrado_causa['UF_RES'].isin(ufs)].copy()

        df_filtrado_uf['DT_INTER'] = pd.to_datetime(df_filtrado_uf['DT_INTER'], errors='coerce')
        df_filtrado_uf.dropna(subset=['DT_INTER'], inplace=True)

        df_historico = df_filtrado_uf.groupby(pd.Grouper(key='DT_INTER', freq='W-Mon'))['N_AIH'].nunique().reset_index()
        df_historico.rename(columns={'DT_INTER': 'ds', 'N_AIH': 'y'}, inplace=True)
        return df_historico
    except Exception as e:
        logger.error(f"ERRO CRÍTICO durante o carregamento de dados SIH: {e}", exc_info=True)
        if task_instance: task_instance.update_state(state='FAILURE', meta={'message': f"Erro ao carregar dados: {str(e)}"})
        return pd.DataFrame()


def executar_previsao(
    ufs: list,
    anos_historico: list,
    cid_codes: list,
    meses_previsao: int,
    output_csv_path: Path, # MODIFICADO: Recebe o caminho completo
    task_instance=None
):
    """ Orquestra todo o processo de previsão de internações. """
    df_historico = carregar_dados_sih(ufs=ufs, anos=anos_historico, cid_codes=cid_codes, task_instance=task_instance)

    if df_historico.empty or df_historico['y'].sum() == 0:
        warning_msg = f"AVISO: Não foram encontrados dados de internação para os filtros aplicados."
        if task_instance: task_instance.update_state(state='FAILURE', meta={'message': warning_msg})
        return None

    df_historico['floor'] = 0
    df_historico['cap'] = df_historico['y'].max() * 1.5
    if df_historico['cap'].iloc[0] == 0: df_historico['cap'] = 1

    modelo = Prophet(yearly_seasonality=True, weekly_seasonality=True, seasonality_mode='multiplicative', growth='logistic')
    modelo.fit(df_historico)

    periodos_futuros = int(np.ceil((meses_previsao * 30.5) / 7))
    futuro = modelo.make_future_dataframe(periods=periodos_futuros, freq='W-Mon')
    futuro['floor'] = 0
    futuro['cap'] = df_historico['cap'].iloc[0]

    previsao = modelo.predict(futuro)
    previsao_final = pd.merge(previsao, df_historico[['ds', 'y']], on='ds', how='left')
    previsao_final = previsao_final.replace([np.inf, -np.inf], np.nan).where(pd.notna(previsao_final), None)

    # Garante que o diretório de saída exista e salva o arquivo
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    previsao_final.to_csv(output_csv_path, sep=';', encoding='utf-8-sig', index=False)
    logger.info(f"Previsão em CSV salva em: {output_csv_path}")

    return output_csv_path

# --- Celery Task Principal ---
@shared_task(bind=True)
def run_prediction_pipeline(self, ufs, anos_historico, cid_codes, meses_previsao, user_id, output_filename=None): # ASSINATURA MODIFICADA
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PredictionTaskStatus = apps.get_model('pipeline_predicao_internacoes', 'PredictionTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PredictionTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={ 'user': user, 'status': 'STARTED', 'ufs': ufs, 'anos_historico': anos_historico, 'cid_codes': cid_codes, 'meses_previsao': meses_previsao, 'message': 'Pipeline de predição iniciada.' }
        )

        self.update_state(state='PROGRESS', meta={'progress': 5, 'message': 'Preparando para carregar dados...'})

        # LÓGICA DE NOME DE ARQUIVO E SEGURANÇA ADICIONADA
        if output_filename and output_filename.strip():
            clean_name = output_filename.strip()
            if not clean_name.lower().endswith('.csv'):
                clean_name += '.csv'
            sanitized_filename = secure_filename(clean_name)
            final_filename = sanitized_filename if sanitized_filename else f"predicao_internacoes_{task_id}.csv"
        else:
            final_filename = f"predicao_internacoes_{task_id}.csv"

        prediction_output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "predicoes" / str(task_id)
        final_output_path = prediction_output_dir / final_filename

        output_csv_path = executar_previsao(
            ufs=ufs, anos_historico=anos_historico, cid_codes=cid_codes, meses_previsao=meses_previsao,
            output_csv_path=final_output_path, # Passando o caminho completo
            task_instance=self
        )

        if not output_csv_path or not output_csv_path.exists():
            # RuntimeError (não Exception genérica): o backend do Celery
            # falha ao serializar/desserializar uma exceção 'Exception' pura
            # (KeyError: 'exc_type' em exception_to_python), derrubando o
            # endpoint de status com um 500 em vez de reportar a falha.
            raise RuntimeError("Execução da predição não gerou o arquivo de resultados esperado. "
                                "Provavelmente não há internações suficientes para os CIDs/anos/UFs selecionados.")

        self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Registrando resultados...'})

        # LÓGICA DE DESCRIÇÃO DETALHADA ADICIONADA
        description_text = (
            f"UFs: {', '.join(sorted(ufs))}. "
            f"Anos Históricos: {', '.join(sorted(map(str, anos_historico)))}. "
            f"CIDs: {', '.join(sorted(cid_codes))}. "
            f"Meses Previstos: {meses_previsao}."
        )

        relative_output_path = os.path.relpath(output_csv_path, settings.MEDIA_ROOT)
        output_file_instance, _ = ManagedFile.objects.update_or_create(
            file=relative_output_path,
            defaults={
                'uploader': user,
                'filename': output_csv_path.name,
                'description': description_text, # Usando a nova descrição
                'file_type': 'PREDICTION'
            }
        )
        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Pipeline de predição concluída. Arquivo: {output_file_instance.filename}"
        task_status_entry.output_file = output_file_instance
        task_status_entry.save()

        logger.info("🎉 FLUXO DE PREDIÇÃO CONCLUÍDO! 🎉")
        return {'status': 'SUCCESS', 'message': 'Dados de previsão gerados com sucesso!', 'output_file_id': output_file_instance.id}

    except Exception as e:
        logger.exception(f"Erro inesperado na pipeline de predição {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = f"Falha na pipeline: {str(e)}"
            task_status_entry.save()
        raise
