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

MODEL_DIR = settings.BASE_DIR / 'api' / 'ml_models'
MODEL_PATH = MODEL_DIR / 'modelo_custo_internacao.joblib'


def secure_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    if not filename.strip():
        return "arquivo_sem_nome"
    return filename.strip()


def _get_pandas_categorical(model):
    """Extrai as categorias do modelo LightGBM a partir do dump do booster."""
    model_str = model.booster_.model_to_string()
    for line in model_str.split('\n'):
        if line.startswith('pandas_categorical:'):
            raw = line[len('pandas_categorical:'):].strip()
            import json
            return json.loads(raw)
    return None


@shared_task(bind=True)
def run_cost_prediction(self, user_id, patient_data, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    CustoInternacaoTaskStatus = apps.get_model('pipeline_custo_internacao', 'CustoInternacaoTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = CustoInternacaoTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={'user': user, 'status': 'STARTED', 'patient_data': patient_data}
    )

    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Carregando modelo...'})
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Modelo não encontrado em {MODEL_PATH}. Execute o script de treino primeiro.")

        modelo = joblib.load(MODEL_PATH)
        feature_names = modelo.feature_name_
        pandas_categorical = _get_pandas_categorical(modelo)

        self.update_state(state='PROGRESS', meta={'progress': 25, 'message': 'Preparando dados...'})
        df_internacao = pd.DataFrame([patient_data])

        # Alinhar colunas com o schema do modelo
        for col in feature_names:
            if col not in df_internacao.columns:
                df_internacao[col] = np.nan
        df_internacao = df_internacao[feature_names]

        # Aplicar categorias do modelo
        # pandas_categorical contém 7 entradas (uma por feature categórica):
        #   [0]=DIAG_PRINC, [1]=PROC_REA, [2]=SEXO, [3]=CAR_INT,
        #   [4]=MORTE, [5]=TP_UNID, [6]=ATIVIDAD
        # Mapeamento: pandas_categorical[i] → feature_name_[cat_feature_indices[i]]
        cat_feature_indices = [0, 1, 4, 5, 7, 8, 10]
        if pandas_categorical:
            for pc_idx, feat_idx in enumerate(cat_feature_indices):
                col_name = feature_names[feat_idx]
                cats = pandas_categorical[pc_idx]
                df_internacao[col_name] = pd.Categorical(
                    df_internacao[col_name].astype(str),
                    categories=cats
                )

        # Converter numéricos
        numeric_cols = ['DIAS_PERM', 'IDADE', 'UTI_MES_TO', 'LEITHOSP']
        for col in numeric_cols:
            if col in df_internacao.columns:
                df_internacao[col] = pd.to_numeric(df_internacao[col], errors='coerce')

        self.update_state(state='PROGRESS', meta={'progress': 40, 'message': 'Realizando previsão...'})
        predicao_log = modelo.predict(df_internacao)[0]
        custo_previsto = np.expm1(predicao_log)

        self.update_state(state='PROGRESS', meta={'progress': 60, 'message': 'Gerando explicação SHAP...'})
        explainer = shap.TreeExplainer(modelo)
        shap_explanation = explainer(df_internacao)

        feature_name_map = {
            'DIAG_PRINC': 'Diagnóstico Principal (CID-10)',
            'PROC_REA': 'Procedimento Realizado (SIGTAP)',
            'DIAS_PERM': 'Dias de Permanência',
            'IDADE': 'Idade do Paciente',
            'SEXO': 'Sexo',
            'CAR_INT': 'Caráter da Internação',
            'UTI_MES_TO': 'Total de Diárias de UTI',
            'MORTE': 'Desfecho Óbito',
            'TP_UNID': 'Tipo de Unidade Hospitalar',
            'LEITHOSP': 'Nº Total de Leitos do Hospital',
            'ATIVIDAD': 'Hospital de Ensino/Pesquisa'
        }

        df_internacao_renamed = df_internacao.rename(columns=feature_name_map)

        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': 'Salvando resultados...'})

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "custo_internacao"
        output_dir.mkdir(parents=True, exist_ok=True)

        desc_parts = [
            f"Custo Estimado: R$ {custo_previsto:,.2f}",
            f"Idade: {patient_data.get('IDADE')}",
            f"Dias de Permanência: {patient_data.get('DIAS_PERM')}",
            f"Diagnóstico: {patient_data.get('DIAG_PRINC')}",
            f"Procedimento: {patient_data.get('PROC_REA')}",
        ]
        csv_description = ". ".join(part for part in desc_parts if part is not None) + "."

        resultado_df = pd.DataFrame([patient_data])
        resultado_df['CUSTO_PREVISTO'] = custo_previsto
        resultado_df['TASK_ID'] = str(task_id)

        csv_filename_base = output_filename or f"previsao_custo_{task_id}"
        csv_filename = secure_filename(f"{csv_filename_base}.csv")
        csv_path = output_dir / csv_filename
        resultado_df.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
        output_csv_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_csv_path,
            filename=csv_filename,
            description=csv_description,
            file_type=FileType.COST_PREDICTION,
            task_id=task_id
        )

        fig, ax = plt.subplots(figsize=(12, 8))
        shap.waterfall_plot(shap_explanation[0], max_display=15, show=False)
        plt.title("Fatores que Influenciam o Custo Previsto (SHAP)", fontsize=14)
        plt.tight_layout()

        image_filename_base = output_filename or f"shap_custo_{task_id}"
        image_filename = secure_filename(f"{image_filename_base}.png")
        image_path = output_dir / image_filename
        plt.savefig(image_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        relative_image_path = os.path.relpath(image_path, settings.MEDIA_ROOT)
        output_image_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_image_path,
            filename=image_filename,
            description=f"Explicação SHAP da previsão de custo para internação.",
            task_id=task_id,
            file_type='OTHER'
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.custo_previsto = custo_previsto
        task_status_entry.output_file = output_csv_file
        task_status_entry.output_image_file = output_image_file
        task_status_entry.message = csv_description
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'custo_previsto': custo_previsto,
            'output_csv_id': output_csv_file.id,
            'output_image_id': output_image_file.id
        }

    except Exception as e:
        logger.exception(f"Falha na pipeline de previsão de custo {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
