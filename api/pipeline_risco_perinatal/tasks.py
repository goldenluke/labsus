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
import json
import joblib
import shap
from api.models import FileType

logger = logging.getLogger(__name__)

MODEL_DIR = settings.BASE_DIR / 'api' / 'ml_models'
MODEL_PATH = MODEL_DIR / 'modelo_risco_perinatal.joblib'

FEATURE_NAMES = [
    'IDADEMAE', 'ESCMAE2010', 'RACACORMAE', 'QTDFILVIVO', 'QTDFILMORT',
    'CONSPRENAT', 'MESPRENAT', 'PARTO', 'GRAVIDEZ', 'ESTCIVMAE'
]

FEATURE_LABELS = {
    'IDADEMAE': 'Idade da Mãe',
    'ESCMAE2010': 'Escolaridade da Mãe',
    'RACACORMAE': 'Raça/Cor da Mãe',
    'QTDFILVIVO': 'Filhos Vivos Anteriores',
    'QTDFILMORT': 'Filhos Mortos Anteriores',
    'CONSPRENAT': 'Consultas Pré-Natal',
    'MESPRENAT': 'Mês Início Pré-Natal',
    'PARTO': 'Tipo de Parto',
    'GRAVIDEZ': 'Tipo de Gravidez',
    'ESTCIVMAE': 'Estado Civil da Mãe',
}

NUMERIC_FEATURES = ['IDADEMAE', 'QTDFILVIVO', 'QTDFILMORT', 'CONSPRENAT', 'MESPRENAT']


def secure_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    if not filename.strip():
        return "arquivo_sem_nome"
    return filename.strip()


def _get_pandas_categorical(model):
    model_str = model.booster_.model_to_string()
    for line in model_str.split('\n'):
        if line.startswith('pandas_categorical:'):
            raw = line[len('pandas_categorical:'):].strip()
            return json.loads(raw)
    return None


def _apply_categoricals(df, model):
    pandas_categorical = _get_pandas_categorical(model)
    feature_names = model.feature_name_
    if not pandas_categorical:
        return df
    cat_cols = ['ESCMAE2010', 'RACACORMAE', 'PARTO', 'GRAVIDEZ', 'ESTCIVMAE']
    for i, fname in enumerate(feature_names):
        if fname in cat_cols:
            idx = feature_names.index(fname)
            cat_group_idx = sum(1 for c in feature_names[:i] if c in cat_cols)
            if cat_group_idx < len(pandas_categorical):
                cats = pandas_categorical[cat_group_idx]
                df[fname] = pd.Categorical(df[fname].astype(str), categories=cats)
    return df


@shared_task(bind=True)
def run_perinatal_risk(self, user_id, patient_data, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PerinatalTaskStatus = apps.get_model('pipeline_risco_perinatal', 'PerinatalTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = PerinatalTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'status': 'STARTED', 'patient_data': patient_data}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Carregando modelo...'})
        model = joblib.load(MODEL_PATH)

        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Preparando dados...'})
        df = pd.DataFrame([patient_data])
        for col in FEATURE_NAMES:
            if col not in df.columns:
                df[col] = np.nan
        df = df[FEATURE_NAMES]
        for col in NUMERIC_FEATURES:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Realizando previsão...'})
        df_clf = _apply_categoricals(df.copy(), model)
        risk_score = float(model.predict_proba(df_clf)[0][1])

        if risk_score < 0.3:
            risk_classification = 'BAIXO'
        elif risk_score < 0.7:
            risk_classification = 'MODERADO'
        else:
            risk_classification = 'ALTO'

        self.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Gerando explicação SHAP...'})
        df_shap = _apply_categoricals(df.copy(), model)
        explainer = shap.TreeExplainer(model)
        shap_explanation = explainer(df_shap)

        shap_values = shap_explanation.values[0].tolist()
        base_value = float(shap_explanation.base_values[0])

        feature_display = [FEATURE_LABELS.get(f, f) for f in FEATURE_NAMES]
        feature_values = df.iloc[0].tolist()

        shap_data = {
            'feature_names': feature_display,
            'feature_values': feature_values,
            'shap_values': shap_values,
            'base_value': base_value,
            'prediction': risk_score,
        }

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})
        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "risco_perinatal"
        output_dir.mkdir(parents=True, exist_ok=True)

        resultado_df = pd.DataFrame([patient_data])
        resultado_df['RISCO_PERINATAL'] = risk_score
        resultado_df['CLASSIFICACAO'] = risk_classification

        dept_label = 'Risco Perinatal'
        csv_desc = (
            f"{dept_label}. "
            f"Classificação: {risk_classification} (p={risk_score:.2f}). "
        )

        csv_filename_base = output_filename or f"risco_perinatal_{task_id}"
        csv_filename = secure_filename(f"{csv_filename_base}.csv")
        csv_path = output_dir / csv_filename
        resultado_df.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
        output_csv_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_csv_path,
            filename=csv_filename,
            description=csv_desc,
            file_type=FileType.RISK_PRENATAL,
            task_id=task_id
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.risk_score = risk_score
        task_status_entry.risk_classification = risk_classification
        task_status_entry.shap_data = shap_data
        task_status_entry.output_file = output_csv_file
        task_status_entry.message = f"Previsão concluída. Risco: {risk_score:.2%} ({risk_classification})"
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'risk_score': risk_score,
            'risk_classification': risk_classification,
            'shap_data': shap_data,
            'output_csv_id': output_csv_file.id,
        }

    except Exception as e:
        logger.exception(f"Falha na pipeline de risco perinatal {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
