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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re
import unicodedata
from api.models import FileType

logger = logging.getLogger(__name__)

MODEL_DIR = settings.BASE_DIR / 'api' / 'ml_models' / 'los_hibrido'

DEPARTAMENTOS = ['Cirurgia', 'Clinica_Medica', 'Obstetricia', 'Pediatria']

FEATURE_NAMES = ['IDADE', 'UTI_MES_TO', 'LEITHOSP', 'COMPLEXIDADE_MEDIA', 'SEXO', 'CAR_INT', 'TP_UNID', 'ATIVIDAD', 'CAPITULO_CID']

FEATURE_LABELS = {
    'IDADE': 'Idade do Paciente',
    'UTI_MES_TO': 'Total de Diárias de UTI',
    'LEITHOSP': 'Nº Total de Leitos do Hospital',
    'COMPLEXIDADE_MEDIA': 'Complexidade Média',
    'SEXO': 'Sexo',
    'CAR_INT': 'Caráter da Internação',
    'TP_UNID': 'Tipo de Unidade Hospitalar',
    'ATIVIDAD': 'Hospital de Ensino/Pesquisa',
    'CAPITULO_CID': 'Capítulo CID-10',
}


def secure_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    if not filename.strip():
        return "arquivo_sem_nome"
    return filename.strip()


def _load_department_models(departamento):
    dept_dir = MODEL_DIR / departamento
    classificador = joblib.load(dept_dir / 'classificador_permanencia.joblib')
    regressor_curta = joblib.load(dept_dir / 'regressor_curta.joblib')
    regressor_longa = joblib.load(dept_dir / 'regressor_longa.joblib')
    return classificador, regressor_curta, regressor_longa


def _get_pandas_categorical(model):
    model_str = model.booster_.model_to_string()
    for line in model_str.split('\n'):
        if line.startswith('pandas_categorical:'):
            import json
            raw = line[len('pandas_categorical:'):].strip()
            return json.loads(raw)
    return None


def _apply_categoricals(df, model):
    pandas_categorical = _get_pandas_categorical(model)
    feature_names = model.feature_name_
    if not pandas_categorical:
        return df
    cat_feature_indices = [i for i, f in enumerate(feature_names) if f in ('SEXO', 'CAR_INT', 'TP_UNID', 'ATIVIDAD', 'CAPITULO_CID')]
    for pc_idx, feat_idx in enumerate(cat_feature_indices):
        col_name = feature_names[feat_idx]
        cats = pandas_categorical[pc_idx]
        df[col_name] = pd.Categorical(df[col_name].astype(str), categories=cats)
    return df


@shared_task(bind=True)
def run_los_prediction(self, user_id, patient_data, departamento, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    LosHibridoTaskStatus = apps.get_model('pipeline_los_hibrido', 'LosHibridoTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = LosHibridoTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={
            'user': user,
            'status': 'STARTED',
            'patient_data': patient_data,
            'departamento': departamento,
        }
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Carregando modelos de {departamento}...'})
        classificador, regressor_curta, regressor_longa = _load_department_models(departamento)

        self.update_state(state='PROGRESS', meta={'progress': 25, 'message': 'Preparando dados...'})
        df = pd.DataFrame([patient_data])

        for col in FEATURE_NAMES:
            if col not in df.columns:
                df[col] = np.nan
        df = df[FEATURE_NAMES]

        for col in FEATURE_NAMES:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        self.update_state(state='PROGRESS', meta={'progress': 40, 'message': 'Classificando permanência...'})
        df_clf = _apply_categoricals(df.copy(), classificador)
        prob_longa = classificador.predict_proba(df_clf)[0][1]
        classificacao = 'Longa' if prob_longa >= 0.5 else 'Curta'

        self.update_state(state='PROGRESS', meta={'progress': 55, 'message': f'Estimando dias ({classificacao})...'})
        if classificacao == 'Longa':
            df_reg = _apply_categoricals(df.copy(), regressor_longa)
            previsao_dias = float(regressor_longa.predict(df_reg)[0])
        else:
            df_reg = _apply_categoricals(df.copy(), regressor_curta)
            previsao_dias = float(regressor_curta.predict(df_reg)[0])
        previsao_dias = max(1.0, round(previsao_dias, 1))

        self.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Gerando explicação SHAP...'})
        modelo_shap = regressor_longa if classificacao == 'Longa' else regressor_curta
        df_shap = _apply_categoricals(df.copy(), modelo_shap)
        explainer = shap.TreeExplainer(modelo_shap)
        shap_explanation = explainer(df_shap)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})
        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "los_hibrido"
        output_dir.mkdir(parents=True, exist_ok=True)

        resultado_df = pd.DataFrame([patient_data])
        resultado_df['DEPARTAMENTO'] = departamento
        resultado_df['PERMANENCIA_CLASSIFICADA'] = classificacao
        resultado_df['PROBABILIDADE_LONGA'] = round(prob_longa, 4)
        resultado_df['PREVISAO_DIAS'] = previsao_dias
        resultado_df['TASK_ID'] = str(task_id)

        dept_label = {'Cirurgia': 'Cirurgia', 'Clinica_Medica': 'Clínica Médica', 'Obstetricia': 'Obstetrícia', 'Pediatria': 'Pediatria'}.get(departamento, departamento)
        csv_desc = (
            f"LOS Híbrido - {dept_label}. "
            f"Classificação: {classificacao} (p={prob_longa:.2f}). "
            f"Previsão: {previsao_dias} dias."
        )

        csv_filename_base = output_filename or f"los_hibrido_{task_id}"
        csv_filename = secure_filename(f"{csv_filename_base}.csv")
        csv_path = output_dir / csv_filename
        resultado_df.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
        output_csv_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_csv_path,
            filename=csv_filename,
            description=csv_desc,
            file_type=FileType.LOS_HIBRIDO,
            task_id=task_id
        )

        fig, ax = plt.subplots(figsize=(12, 8))
        shap.waterfall_plot(shap_explanation[0], max_display=15, show=False)
        plt.title(f"SHAP - LOS {dept_label} ({classificacao})", fontsize=14)
        plt.tight_layout()

        image_filename = secure_filename(f"shap_los_{departamento}_{task_id}.png")
        image_path = output_dir / image_filename
        plt.savefig(image_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        relative_image_path = os.path.relpath(image_path, settings.MEDIA_ROOT)
        output_image_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_image_path,
            filename=image_filename,
            description=f"Explicação SHAP - LOS Híbrido {dept_label}",
            task_id=task_id,
            file_type='OTHER'
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.permanencia_classificada = classificacao
        task_status_entry.probabilidade_longa = prob_longa
        task_status_entry.previsao_dias = previsao_dias
        task_status_entry.output_file = output_csv_file
        task_status_entry.output_image_file = output_image_file
        task_status_entry.message = csv_desc
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'departamento': departamento,
            'permanencia_classificada': classificacao,
            'probabilidade_longa': prob_longa,
            'previsao_dias': previsao_dias,
            'output_csv_id': output_csv_file.id,
            'output_image_id': output_image_file.id,
        }

    except Exception as e:
        logger.exception(f"Falha na pipeline LOS Híbrido {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
