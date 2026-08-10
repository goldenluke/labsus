from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import os
import re
import unicodedata
import joblib

from pysus.online_data.SIH import SIH
from pysus.online_data.SIA import SIA

from api.models import FileType

logger = logging.getLogger(__name__)

MODEL_DIR = settings.BASE_DIR / 'api' / 'ml_models'
MODEL_PATH = MODEL_DIR / 'modelo_doencas_cronicas.joblib'

CACHE_DIR = Path(settings.MEDIA_ROOT) / 'cache' / 'doencas_cronicas'

FEATURE_NAMES = ['N_INTERNACOES_12M', 'TOTAL_DIAS_PERM_12M', 'N_CONSULTAS_AMB_12M', 'IDADE']

FEATURE_LABELS = {
    'N_INTERNACOES_12M': 'Nº Internações (12m)',
    'TOTAL_DIAS_PERM_12M': 'Dias de Permanência (12m)',
    'N_CONSULTAS_AMB_12M': 'Nº Consultas Ambulatoriais (12m)',
    'IDADE': 'Idade',
}

COLS_TO_PRESERVE_AS_OBJECT = [
    'DIAG_PRINC', 'DIAG_SECUN', 'CAUSABAS',
    'PA_CIDPRI', 'PA_CIDSEC', 'PA_CIDCAS',
    'CNES', 'CODESTAB', 'PA_CODUNI',
    'CODMUNRES', 'PA_MUNPCN', 'MUNIC_RES', 'MUNIC_MOV',
    'PROC_REA', 'PA_PROC_ID',
    'SEXO', 'CS_SEXO', 'PA_SEXO',
    'RACA_COR', 'CS_RACA', 'PA_RACACOR',
    'CAR_INT', 'PA_CATEND',
    'TP_UNID', 'PA_TPUPS',
    'NAT_JUR', 'PA_NAT_JUR',
    'ATIVIDAD', 'PA_DOCORIG',
]


def secure_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    if not filename.strip():
        return "arquivo_sem_nome"
    return filename.strip()


def _otimizar_memoria(df):
    for col in df.columns:
        if col in COLS_TO_PRESERVE_AS_OBJECT:
            if df[col].dtype != object:
                df[col] = df[col].astype(str)
            continue
        df_col = pd.to_numeric(df[col], errors='coerce')
        if not df_col.isnull().all():
            col_type = df_col.dtype
            if col_type != object and 'datetime' not in str(col_type):
                c_min, c_max = df_col.min(), df_col.max()
                if str(col_type)[:3] in ('int', 'uin'):
                    for np_type in (np.int8, np.int16, np.int32, np.int64):
                        info = np.iinfo(np_type)
                        if c_min > info.min and c_max < info.max:
                            df[col] = df_col.astype(np_type)
                            break
                else:
                    if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df_col.astype(np.float32)
                    else:
                        df[col] = df_col.astype(np.float64)
    return df


def _carregar_ano(uf, ano, grupo_sih='RD', grupo_sia='PA'):
    """Carrega (com cache local em parquet) um ano de SIH e SIA para uma UF."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sih_path = CACHE_DIR / f"sih_{uf.lower()}_{ano}.parquet"
    sia_path = CACHE_DIR / f"sia_{uf.lower()}_{ano}.parquet"

    if sih_path.exists():
        df_sih = pd.read_parquet(sih_path)
    else:
        sih_db = SIH().load()
        files_sih = sih_db.get_files(group=grupo_sih, uf=[uf], year=[ano])
        df_sih = pd.concat([p.to_dataframe() for p in sih_db.download(files_sih)], ignore_index=True) if files_sih else pd.DataFrame()
        if not df_sih.empty:
            df_sih = _otimizar_memoria(df_sih)
            df_sih.to_parquet(sih_path, index=False)

    if sia_path.exists():
        df_sia = pd.read_parquet(sia_path)
    else:
        sia_db = SIA().load()
        files_sia = sia_db.get_files(group=grupo_sia, uf=[uf], year=[ano])
        df_sia = pd.concat([p.to_dataframe() for p in sia_db.download(files_sia)], ignore_index=True) if files_sia else pd.DataFrame()
        if not df_sia.empty:
            df_sia = _otimizar_memoria(df_sia)
            df_sia.to_parquet(sia_path, index=False)

    return df_sih, df_sia


def _criar_ids_de_paciente(df_sih, df_sia):
    df_sih = df_sih.copy()
    df_sih['ID_PACIENTE'] = df_sih['NASC'].astype(str) + '_' + df_sih['SEXO'].astype(str) + '_' + df_sih['MUNIC_RES'].astype(str)

    df_sia = df_sia.copy()
    required_sia_cols = ['PA_DOCORIG', 'PA_IDADE', 'PA_SEXO', 'PA_MUNPCN', 'PA_CMP']
    if not all(col in df_sia.columns for col in required_sia_cols):
        df_sia['ID_PACIENTE'] = np.nan
    else:
        df_sia_ind = df_sia[df_sia['PA_DOCORIG'].isin(['I', 'P', 'S', 'A', 'R'])].copy()
        df_sia_ind['ANO_ATENDIMENTO'] = pd.to_datetime(df_sia_ind['PA_CMP'], format='%Y%m', errors='coerce').dt.year
        df_sia_ind['ANO_NASC_APROX'] = df_sia_ind['ANO_ATENDIMENTO'] - pd.to_numeric(df_sia_ind['PA_IDADE'], errors='coerce')
        df_sia_ind['ID_PACIENTE'] = (
            df_sia_ind['ANO_NASC_APROX'].astype(str) + '_' +
            df_sia_ind['PA_SEXO'].astype(str) + '_' +
            df_sia_ind['PA_MUNPCN'].astype(str)
        )
        df_sia = df_sia.merge(df_sia_ind[['ID_PACIENTE']], left_index=True, right_index=True, how='left')

    df_sih.dropna(subset=['ID_PACIENTE'], inplace=True)
    df_sia.dropna(subset=['ID_PACIENTE'], inplace=True)
    return df_sih, df_sia


def _construir_dataset_longitudinal(df_sih, df_sia, cid_doenca, ano_snapshot):
    df_sih_filtrado = df_sih.dropna(subset=['DIAG_PRINC', 'ID_PACIENTE'])
    df_sia_filtrado = df_sia.dropna(subset=['PA_CIDPRI', 'ID_PACIENTE'])

    pacientes_sih = set(df_sih_filtrado[df_sih_filtrado['DIAG_PRINC'].astype(str).str.startswith(cid_doenca, na=False)]['ID_PACIENTE'])
    pacientes_sia = set(df_sia_filtrado[df_sia_filtrado['PA_CIDPRI'].astype(str).str.startswith(cid_doenca, na=False)]['ID_PACIENTE'])
    pacientes_coorte = pacientes_sih | pacientes_sia

    if not pacientes_coorte:
        return pd.DataFrame()

    df_sih = df_sih.copy()
    df_sia = df_sia.copy()
    df_sih['DATA'] = pd.to_datetime(df_sih['DT_INTER'], format='%Y%m%d', errors='coerce')
    df_sia['DATA'] = pd.to_datetime(df_sia['PA_CMP'], format='%Y%m', errors='coerce')
    df_sih_coorte = df_sih[df_sih['ID_PACIENTE'].isin(pacientes_coorte)].dropna(subset=['DATA'])
    df_sia_coorte = df_sia[df_sia['ID_PACIENTE'].isin(pacientes_coorte)].dropna(subset=['DATA'])

    snapshot_date = pd.to_datetime(f"{ano_snapshot}-01-01")
    history_start_date = snapshot_date - pd.DateOffset(months=12)
    future_end_date = snapshot_date + pd.DateOffset(months=6)

    lista_pacientes_features = []
    for paciente_id in pacientes_coorte:
        hist_sih = df_sih_coorte[(df_sih_coorte['ID_PACIENTE'] == paciente_id) & (df_sih_coorte['DATA'] >= history_start_date) & (df_sih_coorte['DATA'] < snapshot_date)]
        hist_sia = df_sia_coorte[(df_sia_coorte['ID_PACIENTE'] == paciente_id) & (df_sia_coorte['DATA'] >= history_start_date) & (df_sia_coorte['DATA'] < snapshot_date)]

        if hist_sih.empty and hist_sia.empty:
            continue

        idade_sih = pd.to_numeric(hist_sih['IDADE'], errors='coerce')
        idade_sia = pd.to_numeric(hist_sia['PA_IDADE'], errors='coerce')
        idade = np.nan
        if not idade_sih.empty and idade_sih.max() is not np.nan:
            idade = idade_sih.max()
        elif not idade_sia.empty and idade_sia.max() is not np.nan:
            idade = idade_sia.max()

        features = {
            'ID_PACIENTE': paciente_id,
            'N_INTERNACOES_12M': len(hist_sih),
            'TOTAL_DIAS_PERM_12M': pd.to_numeric(hist_sih['DIAS_PERM'], errors='coerce').sum(),
            'N_CONSULTAS_AMB_12M': len(hist_sia),
            'IDADE': idade,
        }

        futuro_sih = df_sih_coorte[(df_sih_coorte['ID_PACIENTE'] == paciente_id) & (df_sih_coorte['DATA'] >= snapshot_date) & (df_sih_coorte['DATA'] < future_end_date)]
        features['ALVO_HOSPITALIZADO_6M'] = 1 if not futuro_sih.empty else 0

        lista_pacientes_features.append(features)

    return pd.DataFrame(lista_pacientes_features)


@shared_task(bind=True)
def run_doencas_cronicas(self, user_id, uf, cid_doenca='I50', ano_snapshot=None, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    DoencasCronicasTaskStatus = apps.get_model('pipeline_doencas_cronicas', 'DoencasCronicasTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = DoencasCronicasTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'status': 'STARTED', 'uf': uf, 'cid_doenca': cid_doenca, 'ano_snapshot': ano_snapshot}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Carregando dados históricos (SIH/SIA)...'})
        df_sih_a, df_sia_a = _carregar_ano(uf, ano_snapshot - 1)
        df_sih_b, df_sia_b = _carregar_ano(uf, ano_snapshot)
        df_sih = pd.concat([df_sih_a, df_sih_b], ignore_index=True)
        df_sia = pd.concat([df_sia_a, df_sia_b], ignore_index=True)

        self.update_state(state='PROGRESS', meta={'progress': 35, 'message': 'Construindo coorte de pacientes crônicos...'})
        df_sih, df_sia = _criar_ids_de_paciente(df_sih, df_sia)
        df_analitico = _construir_dataset_longitudinal(df_sih, df_sia, cid_doenca, ano_snapshot)
        df_analitico.dropna(subset=['IDADE'], inplace=True)

        if df_analitico.empty:
            raise ValueError("Nenhum paciente encontrado para a coorte com os parâmetros informados.")

        self.update_state(state='PROGRESS', meta={'progress': 55, 'message': 'Carregando modelo preditivo...'})
        model_bundle = joblib.load(MODEL_PATH)
        model = model_bundle['model']

        self.update_state(state='PROGRESS', meta={'progress': 65, 'message': 'Pontuando pacientes...'})
        X = df_analitico[FEATURE_NAMES]
        df_analitico['PROB_HOSPITALIZACAO_6M'] = model.predict_proba(X)[:, 1]

        roc_auc = None
        if df_analitico['ALVO_HOSPITALIZADO_6M'].nunique() == 2:
            from sklearn.metrics import roc_auc_score
            roc_auc = float(roc_auc_score(df_analitico['ALVO_HOSPITALIZADO_6M'], df_analitico['PROB_HOSPITALIZACAO_6M']))

        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': 'Gerando explicação SHAP (importância global)...'})
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        order = np.argsort(mean_abs_shap)[::-1]
        shap_data = {
            'feature_names': [FEATURE_LABELS.get(FEATURE_NAMES[i], FEATURE_NAMES[i]) for i in order],
            'shap_values': [float(mean_abs_shap[i]) for i in order],
        }

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Salvando resultados...'})
        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "doencas_cronicas"
        output_dir.mkdir(parents=True, exist_ok=True)

        n_pacientes = len(df_analitico)
        dept_label = 'Doenças Crônicas'
        csv_desc = (
            f"{dept_label}. UF: {uf}. CID: {cid_doenca}. "
            f"Coorte: {n_pacientes} pacientes. "
            + (f"AUC: {roc_auc:.3f}." if roc_auc is not None else "")
        )

        csv_filename_base = output_filename or f"doencas_cronicas_{task_id}"
        csv_filename = secure_filename(f"{csv_filename_base}.csv")
        csv_path = output_dir / csv_filename
        df_analitico.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
        output_csv_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_csv_path,
            filename=csv_filename,
            description=csv_desc,
            file_type=FileType.DOENCAS_CRONICAS,
            task_id=task_id
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.n_pacientes_coorte = n_pacientes
        task_status_entry.roc_auc = roc_auc
        task_status_entry.shap_data = shap_data
        task_status_entry.output_file = output_csv_file
        task_status_entry.message = f"Coorte pontuada: {n_pacientes} pacientes." + (f" AUC: {roc_auc:.3f}." if roc_auc is not None else "")
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'n_pacientes_coorte': n_pacientes,
            'roc_auc': roc_auc,
            'shap_data': shap_data,
            'output_csv_id': output_csv_file.id,
        }

    except Exception as e:
        logger.exception(f"Falha na pipeline de doenças crônicas {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
