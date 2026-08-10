from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
from pathlib import Path
import logging
import os
import re
import unicodedata

from pysus.online_data.SIH import download as download_sih
from api.models import FileType

logger = logging.getLogger(__name__)

# Mapeamento de Código IBGE do Estado para a Sigla da UF
UF_CODE_TO_ABBREVIATION = {
    '12': 'AC', '27': 'AL', '16': 'AP', '13': 'AM', '29': 'BA', '23': 'CE',
    '53': 'DF', '32': 'ES', '52': 'GO', '21': 'MA', '51': 'MT', '50': 'MS',
    '31': 'MG', '15': 'PA', '25': 'PB', '41': 'PR', '26': 'PE', '22': 'PI',
    '33': 'RJ', '24': 'RN', '43': 'RS', '11': 'RO', '14': 'RR', '42': 'SC',
    '35': 'SP', '28': 'SE', '17': 'TO'
}

def secure_filename(filename):
    """
    Sanitiza um nome de arquivo para ser seguro, mas permite espaços.
    - Normaliza para remover acentos.
    - Remove caracteres perigosos ou inválidos em sistemas de ficheiros.
    - Mantém espaços.
    """
    # Normaliza para o formato NKFD para separar caracteres de acentos e remove-os
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')

    # Remove caracteres que são inválidos na maioria dos sistemas de ficheiros ou perigosos (path traversal)
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)

    # Remove pontos no início do nome do ficheiro para evitar ficheiros ocultos
    if filename.startswith('.'):
        filename = filename[1:]



    return filename.strip() # Remove espaços no início/fim

def run_fluxo_analysis_logic(ufs, anos, diagnostico_cids, min_pacientes_fluxo, task_instance=None):
    """
    Executa a lógica principal da análise de fluxo de pacientes e retorna um DataFrame com os resultados.
    """
    if task_instance:
        task_instance.update_state(state='PROGRESS', meta={'progress': 5, 'message': 'Carregando dados de referência...'})

    caminho_municipios_csv = settings.BASE_DIR / 'referencia' / 'espaciais' / 'csv' / 'municipios.csv'
    try:
        df_municipios = pd.read_csv(caminho_municipios_csv, dtype={'codigo_ibge': str, 'codigo_uf': str})
    except FileNotFoundError as e:
        raise Exception(f"Arquivo de referência de municípios não encontrado: {e}")

    if task_instance:
        task_instance.update_state(state='PROGRESS', meta={'progress': 15, 'message': 'Baixando dados do SIH...'})

    df_list = []
    for uf in ufs:
        for ano in anos:
            try:
                downloaded_files = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
                df_anual_uf = pd.DataFrame()

                if isinstance(downloaded_files, list):
                    monthly_dfs = [f.to_dataframe() for f in downloaded_files if hasattr(f, 'to_dataframe')]
                    if monthly_dfs:
                        df_anual_uf = pd.concat(monthly_dfs, ignore_index=True)
                elif hasattr(downloaded_files, 'to_dataframe'):
                    df_anual_uf = downloaded_files.to_dataframe()

                if not df_anual_uf.empty:
                    df_list.append(df_anual_uf)
            except Exception as e:
                logger.warning(f"Não foi possível baixar ou processar dados para {uf}/{ano}: {e}")

    if not df_list: raise Exception("Nenhum dado do SIH pôde ser baixado.")
    df_total = pd.concat(df_list, ignore_index=True)

    if task_instance:
        task_instance.update_state(state='PROGRESS', meta={'progress': 60, 'message': 'Processando fluxos...'})

    df_diagnostico = df_total[df_total['DIAG_PRINC'].str.startswith(tuple(diagnostico_cids))].copy()
    if df_diagnostico.empty: raise Exception("Nenhum registro para os CIDs especificados foi encontrado.")

    # CORREÇÃO: Removida a coluna 'VAL_TOT' que estava com formato inválido
    df_fluxo = df_diagnostico[['MUNIC_RES', 'MUNIC_MOV', 'N_AIH']].dropna()
    df_fluxo['MUNIC_RES'] = df_fluxo['MUNIC_RES'].astype(str).str[:6]
    df_fluxo['MUNIC_MOV'] = df_fluxo['MUNIC_MOV'].astype(str).str[:6]
    df_fluxo = df_fluxo[df_fluxo['MUNIC_RES'] != df_fluxo['MUNIC_MOV']]

    # CORREÇÃO: Agrupamento agora conta apenas os pacientes (N_AIH)
    df_fluxo_agg = df_fluxo.groupby(['MUNIC_RES', 'MUNIC_MOV']).agg(
        N_PACIENTES=('N_AIH', 'nunique')
    ).reset_index()

    df_fluxo_agg = df_fluxo_agg[df_fluxo_agg['N_PACIENTES'] >= min_pacientes_fluxo]

    if df_fluxo_agg.empty: raise Exception(f"Nenhuma rota de fluxo com no mínimo {min_pacientes_fluxo} pacientes encontrada.")

    df_coords = df_municipios[['codigo_ibge', 'latitude', 'longitude', 'nome', 'codigo_uf']].copy()
    df_coords['codigo_ibge'] = df_coords['codigo_ibge'].str[:6]
    df_coords['uf_sigla'] = df_coords['codigo_uf'].map(UF_CODE_TO_ABBREVIATION)

    df_final = pd.merge(df_fluxo_agg, df_coords, left_on='MUNIC_RES', right_on='codigo_ibge', how='inner').rename(columns={'latitude': 'lat_origem', 'longitude': 'lon_origem', 'nome': 'municipio_origem', 'uf_sigla': 'uf_origem'}).drop(['codigo_ibge', 'codigo_uf'], axis=1)
    df_final = pd.merge(df_final, df_coords, left_on='MUNIC_MOV', right_on='codigo_ibge', how='inner').rename(columns={'latitude': 'lat_destino', 'longitude': 'lon_destino', 'nome': 'municipio_destino', 'uf_sigla': 'uf_destino'}).drop(['codigo_ibge', 'codigo_uf'], axis=1)

    return df_final

@shared_task(bind=True)
def run_fluxo_pacientes_pipeline(self, user_id, ufs, anos, diagnostico_cids, min_pacientes_fluxo, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    FluxoPacientesTaskStatus = apps.get_model('pipeline_fluxo_pacientes', 'FluxoPacientesTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    params_to_save = {
        'ufs': ufs, 'anos': anos, 'diagnostico_cids': diagnostico_cids,
        'min_pacientes_fluxo': min_pacientes_fluxo
    }

    try:
        task_status_entry, _ = FluxoPacientesTaskStatus.objects.get_or_create(
            task_id=task_id, defaults={'user': user, 'status': 'STARTED', **params_to_save, 'message': 'Pipeline iniciada.'}
        )

        df_results = run_fluxo_analysis_logic(
            ufs=ufs, anos=anos, diagnostico_cids=diagnostico_cids,
            min_pacientes_fluxo=min_pacientes_fluxo, task_instance=self
        )

        self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Salvando arquivo de resultado...'})

        cid_based_name = '-'.join(diagnostico_cids)
        final_filename = output_filename or f"fluxo_{cid_based_name.lower()}_{task_id[:8]}.csv"
        final_filename = secure_filename(final_filename)

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "fluxo_pacientes" / str(task_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / final_filename
        df_results.to_csv(csv_path, index=False, sep=';', decimal=',')

        desc = (f"UFs: {', '.join(ufs)}. Anos: {', '.join(map(str, anos))}. "
                f"CIDs: {', '.join(diagnostico_cids)}. "
                f"Min. Pacientes: {min_pacientes_fluxo}.")

        output_file = ManagedFile.objects.create(
            uploader=user, file=os.path.relpath(csv_path, settings.MEDIA_ROOT),
            filename=final_filename, description=desc, file_type=FileType.PATIENT_FLOW
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = "Análise de fluxo concluída com sucesso."
        task_status_entry.output_file = output_file
        task_status_entry.save()

        return {'status': 'SUCCESS', 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na pipeline de fluxo de pacientes {task_id}.")
        if 'task_status_entry' in locals() and task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise
