from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import os
import joblib
import shap
import re
import unicodedata
from api.models import FileType

logger = logging.getLogger(__name__)

MODEL_DIR = settings.BASE_DIR / 'api' / 'ml_models'
MODEL_PATH = MODEL_DIR / 'lgbm_readmission_model.joblib'
X_TEST_PATH = MODEL_DIR / 'X_test.parquet'
COX_MODEL_PATH = MODEL_DIR / 'modelo_cox_readmissao.joblib'

def secure_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    if not filename.strip():
        return "arquivo_sem_nome"
    return filename.strip()

def engineer_features_for_patient(patient_df):
    logger.info("Aplicando engenharia de atributos...")
    patient_df['CAPITULO_CID'] = patient_df['DIAG_PRINC'].str[0]
    patient_df = patient_df.drop(columns=['DIAG_PRINC'])
    logger.info("Features transformadas com sucesso.")
    return patient_df

@shared_task(bind=True)
def run_readmission_prediction(self, user_id, patient_data, output_filename=None, output_csv_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    ReadmissaoTaskStatus = apps.get_model('pipeline_risco_readmissao', 'ReadmissaoTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = ReadmissaoTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'status': 'STARTED', 'patient_data': patient_data}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Carregando modelo...'})
        model = joblib.load(MODEL_PATH)
        X_test = pd.read_parquet(X_TEST_PATH)
        explainer = shap.TreeExplainer(model)
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Preparando dados...'})
        patient_df_raw = pd.DataFrame([patient_data])
        patient_df_featured = engineer_features_for_patient(patient_df_raw)
        patient_df = patient_df_featured.reindex(columns=X_test.columns, fill_value=np.nan)
        for col in X_test.columns:
            if X_test[col].dtype.name == 'category':
                patient_df[col] = pd.Categorical(patient_df[col], categories=X_test[col].cat.categories)
            else:
                patient_df[col] = pd.to_numeric(patient_df[col], errors='coerce')
        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Realizando previsão...'})
        prediction_proba = model.predict_proba(patient_df)
        risk_score = prediction_proba[0, 1]
        self.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Gerando explicação...'})
        shap_values = explainer.shap_values(patient_df)
        if isinstance(shap_values, list): shap_values_risk = shap_values[1]
        else: shap_values_risk = shap_values
        if isinstance(explainer.expected_value, list): base_value = explainer.expected_value[1]
        else: base_value = explainer.expected_value

        feature_name_map = {
            'IDADE': 'Idade', 'DIAS_PERM': 'Dias de Permanência',
            'N_COMORBIDADES': 'Nº Comorbidades', 'USOU_UTI': 'Utilizou UTI',
            'CAPITULO_CID': 'Grupo do Diagnóstico', 'DIAS_PERM': 'Dias de Permanência',
            'SEXO': 'Sexo', 'RACA_COR': 'Raça/Cor', 'CAR_INT': 'Caráter da Internação',
            'HOSP_NATUREZA': 'Natureza do Hospital', 'HOSP_LEITOS': 'Nº de Leitos do Hospital'
        }

        feature_names = [feature_name_map.get(f, f) for f in patient_df.columns]
        shap_data = {
            'feature_names': feature_names,
            'shap_values': [round(float(v), 6) for v in shap_values_risk[0]],
            'base_value': round(float(base_value), 6),
        }

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Salvando resultados...'})

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "readmissao"
        output_dir.mkdir(parents=True, exist_ok=True)

        desc_parts = [
            f"Score de Risco Calculado: {risk_score:.2%}",
            f"Idade: {patient_data.get('IDADE')}",
            f"Dias de Permanência: {patient_data.get('DIAS_PERM')}",
            f"Nº de Comorbidades: {patient_data.get('N_COMORBIDADES')}",
            f"Usou UTI: {'Sim' if patient_data.get('USOU_UTI') == 1 else 'Não'}",
            f"Diagnóstico Principal: {patient_data.get('DIAG_PRINC')}"
        ]
        csv_description = ". ".join(part for part in desc_parts if part is not None) + "."

        resultado_df = pd.DataFrame([patient_data])
        resultado_df['RISCO_READMISSAO_30D'] = risk_score
        csv_filename_base = output_csv_filename or f"previsao_paciente_{task_id}"
        csv_filename = secure_filename(f"{csv_filename_base}.csv")
        csv_path = output_dir / csv_filename
        resultado_df.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
        output_csv_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_csv_path,
            filename=csv_filename,
            description=csv_description,
            file_type=FileType.RISK_PREDICTION,
            task_id=task_id
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.risk_score = risk_score
        task_status_entry.output_file = output_csv_file
        task_status_entry.shap_data = shap_data
        task_status_entry.message = f"Previsão concluída. Risco: {risk_score:.2%}"
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'risk_score': risk_score,
            'output_csv_id': output_csv_file.id,
            'shap_data': shap_data,
        }

    except Exception as e:
        logger.exception(f"Falha na pipeline de previsão de readmissão {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise


COX_RAW_INPUT_MAP = {
    'IDADE': 'IDADE',
    'DIAS_PERM': 'DIAS_PERM',
    'UTI_MES_TO': 'UTI_MES_TO',
    'SEXO': 'SEXO',
    'CAR_INT': 'CAR_INT',
    'DIAG_PRINC': 'DIAG_PRINC',
    'TP_UNID': 'TP_UNID',
    'ATIVIDAD': 'ATIVIDAD',
    'MORTE': 'MORTE',
}

COX_ALL_COLUMNS = [
    'IDADE', 'DIAS_PERM', 'UTI_MES_TO',
    'SEXO_3',
    'DIAG_PRINC_CAP_B', 'DIAG_PRINC_CAP_C', 'DIAG_PRINC_CAP_D', 'DIAG_PRINC_CAP_E',
    'DIAG_PRINC_CAP_F', 'DIAG_PRINC_CAP_G', 'DIAG_PRINC_CAP_H', 'DIAG_PRINC_CAP_I',
    'DIAG_PRINC_CAP_J', 'DIAG_PRINC_CAP_K', 'DIAG_PRINC_CAP_L', 'DIAG_PRINC_CAP_M',
    'DIAG_PRINC_CAP_N', 'DIAG_PRINC_CAP_O', 'DIAG_PRINC_CAP_P', 'DIAG_PRINC_CAP_Q',
    'DIAG_PRINC_CAP_R', 'DIAG_PRINC_CAP_S', 'DIAG_PRINC_CAP_T', 'DIAG_PRINC_CAP_Z',
    'CAR_INT_02', 'CAR_INT_05', 'CAR_INT_06',
    'TP_UNID_07',
    'ATIVIDAD_03', 'ATIVIDAD_04',
    'MORTE_1',
]

COX_FEATURE_LABELS = {
    'IDADE': 'Idade',
    'DIAS_PERM': 'Dias de Permanência',
    'UTI_MES_TO': 'Diárias de UTI',
    'SEXO_3': 'Sexo (Feminino)',
    'DIAG_PRINC_CAP_B': 'Doenças Infecciosas',
    'DIAG_PRINC_CAP_C': 'Neoplasias',
    'DIAG_PRINC_CAP_D': 'Doenças do Sangue',
    'DIAG_PRINC_CAP_E': 'Nutricional/Metabólico',
    'DIAG_PRINC_CAP_F': 'Transtornos Mentais',
    'DIAG_PRINC_CAP_G': 'Doenças Digestivas',
    'DIAG_PRINC_CAP_H': 'Doenças da Pele',
    'DIAG_PRINC_CAP_I': 'Doenças Circulatórias',
    'DIAG_PRINC_CAP_J': 'Infecções Respiratórias',
    'DIAG_PRINC_CAP_K': 'Doenças Geniturinárias',
    'DIAG_PRINC_CAP_L': 'Doenças Pele (Adulto)',
    'DIAG_PRINC_CAP_M': 'Doenças Musculoesqueléticas',
    'DIAG_PRINC_CAP_N': 'Sistema Nervoso',
    'DIAG_PRINC_CAP_O': 'Doenças Obstétricas',
    'DIAG_PRINC_CAP_P': 'Gravidez/Parto',
    'DIAG_PRINC_CAP_Q': 'Perinatal',
    'DIAG_PRINC_CAP_R': 'Doenças Respiratórias',
    'DIAG_PRINC_CAP_S': 'Órgãos Sensoriais',
    'DIAG_PRINC_CAP_T': 'Trauma',
    'DIAG_PRINC_CAP_Z': 'Causas Externas',
    'CAR_INT_02': 'Urgência',
    'CAR_INT_05': 'Tratamento Acidente',
    'CAR_INT_06': 'Acidente Trabalho',
    'TP_UNID_07': 'Tipo Unidade 07',
    'ATIVIDAD_03': 'Atividade 03',
    'ATIVIDAD_04': 'Atividade 04',
    'MORTE_1': 'Óbito',
}


def _build_cox_features(patient_data):
    row = {}
    row['IDADE'] = float(patient_data.get('IDADE', 0) or 0)
    row['DIAS_PERM'] = float(patient_data.get('DIAS_PERM', 0) or 0)
    row['UTI_MES_TO'] = float(patient_data.get('UTI_MES_TO', 0) or 0)

    diag_princ = str(patient_data.get('DIAG_PRINC', 'A') or 'A')
    capitulo = diag_princ[0].upper() if diag_princ else 'A'
    for cap in ['B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','Z']:
        row[f'DIAG_PRINC_CAP_{cap}'] = 1 if capitulo == cap else 0

    sexo = str(patient_data.get('SEXO', '1') or '1')
    row['SEXO_3'] = 1 if sexo == '3' else 0

    car_int = str(patient_data.get('CAR_INT', '01') or '01')
    row['CAR_INT_02'] = 1 if car_int == '02' else 0
    row['CAR_INT_05'] = 1 if car_int == '05' else 0
    row['CAR_INT_06'] = 1 if car_int == '06' else 0

    tp_unid = str(patient_data.get('TP_UNID', '01') or '01')
    row['TP_UNID_07'] = 1 if tp_unid == '07' else 0

    atividad = str(patient_data.get('ATIVIDAD', '01') or '01')
    row['ATIVIDAD_03'] = 1 if atividad == '03' else 0
    row['ATIVIDAD_04'] = 1 if atividad == '04' else 0

    morte = str(patient_data.get('MORTE', '0') or '0')
    row['MORTE_1'] = 1 if morte == '1' else 0

    return pd.DataFrame([row])


@shared_task(bind=True)
def run_cox_survival_analysis(self, user_id, patient_data, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    ReadmissaoTaskStatus = apps.get_model('pipeline_risco_readmissao', 'ReadmissaoTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = ReadmissaoTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'status': 'STARTED', 'patient_data': patient_data}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Carregando modelo Cox...'})
        import lifelines
        cox_model = joblib.load(COX_MODEL_PATH)

        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Preparando dados...'})
        df = _build_cox_features(patient_data)
        df = df[COX_ALL_COLUMNS]

        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Calculando sobrevivência...'})
        survival_fn = cox_model.predict_survival_function(df)
        survival_times = survival_fn.index.tolist()
        survival_probs = survival_fn.iloc[:, 0].tolist()
        median_prediction = cox_model.predict_median(df)
        median_survival = float(
            median_prediction.iloc[0]
            if hasattr(median_prediction, 'iloc')
            else np.asarray(median_prediction).reshape(-1)[0]
        )
        if not np.isfinite(median_survival):
            median_survival = None
        partial_hazard_prediction = cox_model.predict_partial_hazard(df)
        partial_hazard = float(
            partial_hazard_prediction.iloc[0]
            if hasattr(partial_hazard_prediction, 'iloc')
            else np.asarray(partial_hazard_prediction).reshape(-1)[0]
        )

        self.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Extraindo hazard ratios...'})
        summary = cox_model.summary
        hazard_ratios = []
        for feat in COX_ALL_COLUMNS:
            if feat in summary.index:
                row = summary.loc[feat]
                label = COX_FEATURE_LABELS.get(feat, feat)
                ci = cox_model.confidence_intervals_.loc[feat] if feat in cox_model.confidence_intervals_.index else [0, 0]
                hazard_ratios.append({
                    'feature': label,
                    'hr': round(float(np.exp(row['coef'])), 3),
                    'ci_lower': round(float(np.exp(ci.iloc[0])), 3) if hasattr(ci, 'iloc') else 0,
                    'ci_upper': round(float(np.exp(ci.iloc[1])), 3) if hasattr(ci, 'iloc') else 0,
                    'p_value': round(float(row['p']), 4),
                })

        hazard_ratios.sort(key=lambda x: x['hr'], reverse=True)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})
        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "cox_readmissao"
        output_dir.mkdir(parents=True, exist_ok=True)

        resultado_df = pd.DataFrame([patient_data])
        resultado_df['COX_PARTIAL_HAZARD'] = partial_hazard
        resultado_df['COX_MEDIAN_SURVIVAL_DAYS'] = median_survival

        csv_desc = (
            f"Cox Readmissão. "
            f"Hazard Parcial: {partial_hazard:.3f}. "
            f"Mediana Sobrevivência: "
            f"{median_survival:.0f} dias." if median_survival is not None
            else f"Cox Readmissão. Hazard Parcial: {partial_hazard:.3f}. "
                 "Mediana Sobrevivência: não estimada."
        )

        csv_filename_base = output_filename or f"cox_readmissao_{task_id}"
        csv_filename = secure_filename(f"{csv_filename_base}.csv")
        csv_path = output_dir / csv_filename
        resultado_df.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
        output_csv_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_csv_path,
            filename=csv_filename,
            description=csv_desc,
            file_type=FileType.COX_READMISSION,
            task_id=task_id
        )

        cox_result_data = {
            'survival_curve': {
                'time': survival_times,
                'probability': survival_probs,
                'median_survival': median_survival,
            },
            'hazard_ratios': hazard_ratios,
            'partial_hazard': partial_hazard,
            'concordance_index': float(cox_model.concordance_index_),
            'patient_data': patient_data,
        }

        task_status_entry.status = 'SUCCESS'
        task_status_entry.output_file = output_csv_file
        task_status_entry.shap_data = cox_result_data
        median_message = (
            f"{median_survival:.0f} dias"
            if median_survival is not None
            else "não estimada"
        )
        task_status_entry.message = f"Cox concluído. Hazard: {partial_hazard:.3f}. Mediana: {median_message}."
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'partial_hazard': partial_hazard,
            'median_survival': median_survival,
            'concordance_index': float(cox_model.concordance_index_),
            'survival_curve': cox_result_data['survival_curve'],
            'hazard_ratios': hazard_ratios,
            'output_csv_id': output_csv_file.id,
        }

    except Exception as e:
        logger.exception(f"Falha na pipeline Cox de readmissão {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
