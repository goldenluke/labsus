from celery import shared_task
from django.conf import settings
from django.apps import apps
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import os
import re

from pysus.online_data.SIH import download as download_sih
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

from api.models import FileType # Importa o Enum FileType

logger = logging.getLogger(__name__)

def secure_filename(filename):
    """Limpa e sanitiza um nome de arquivo para uso seguro no sistema de arquivos."""
    filename = filename.replace('/', '').replace('\\', '')
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    return filename

def run_risk_analysis_logic(ufs, anos, diagnostico_cids, comorbidade_cids, decision_threshold=0.5, task_instance=None):
    """
    Executa a lógica principal da análise de risco, retornando os resultados.
    """
    diagnostico_nome = "-".join(diagnostico_cids)

    # --- 1. Coleta e Preparação dos Dados ---
    df_list = []
    total_steps = len(ufs) * len(anos)
    current_step = 0
    for uf in ufs:
        for ano in anos:
            current_step += 1
            progress = int(10 + (current_step / total_steps) * 40)
            if task_instance:
                task_instance.update_state(state='PROGRESS', meta={'progress': progress, 'message': f'Baixando dados do SIH para {uf}/{ano}...'})
            try:
                downloaded_files = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
                if isinstance(downloaded_files, list):
                    df_sih = pd.concat([f.to_dataframe() for f in downloaded_files], ignore_index=True)
                elif hasattr(downloaded_files, "to_dataframe"):
                    df_sih = downloaded_files.to_dataframe()
                else:
                    df_sih = pd.DataFrame()
                df_list.append(df_sih)
            except Exception as e:
                logger.warning(f"Erro ao baixar dados para {uf}/{ano}: {e}")

    if not df_list or pd.concat(df_list).empty:
        raise Exception("Nenhum dado do SIH pôde ser baixado. Análise abortada.")

    df_total = pd.concat(df_list, ignore_index=True)
    logger.info(f"Total de {len(df_total)} registos de internação baixados.")
    if task_instance:
        task_instance.update_state(state='PROGRESS', meta={'progress': 55, 'message': 'Preparando dados para o modelo...'})

    df_diagnostico = df_total[df_total['DIAG_PRINC'].str.startswith(tuple(diagnostico_cids))].copy()

    features = ['IDADE', 'SEXO', 'CAR_INT', 'RACA_COR', 'DIAGSEC1', 'MORTE']
    df_modelo_raw = df_diagnostico[features].copy()
    df_modelo_raw['MORTE'] = pd.to_numeric(df_modelo_raw['MORTE'], errors='coerce')
    df_modelo_raw.dropna(subset=['MORTE'], inplace=True)

    if len(df_modelo_raw) < 50 or df_modelo_raw['MORTE'].nunique() < 2:
        raise Exception(f"Dados insuficientes para análise. Amostras: {len(df_modelo_raw)}, Classes: {df_modelo_raw['MORTE'].nunique()}")

    # --- 2. Engenharia de Features ---
    df_modelo_raw['TEM_COMORBIDADE'] = df_modelo_raw['DIAGSEC1'].notna().astype(int)
    if comorbidade_cids:
        comorbidade_col_name = f"TEM_COMORB_{'-'.join(comorbidade_cids)}"
        df_modelo_raw[comorbidade_col_name] = df_modelo_raw['DIAGSEC1'].str.startswith(tuple(comorbidade_cids)).fillna(False).astype(int)
    df_modelo_raw['RACA_COR'] = df_modelo_raw['RACA_COR'].fillna('99').astype(str) # Corrigido para 99
    df_modelo = pd.get_dummies(df_modelo_raw.drop('DIAGSEC1', axis=1), columns=['SEXO', 'CAR_INT', 'RACA_COR'], drop_first=True)

    X = df_modelo.drop('MORTE', axis=1)
    y = df_modelo['MORTE']
    scaler = StandardScaler()
    X_scaled = X.copy()
    X_scaled['IDADE'] = scaler.fit_transform(X[['IDADE']])

    # --- 3. Treinamento do Modelo ---
    if task_instance:
        task_instance.update_state(state='PROGRESS', meta={'progress': 80, 'message': 'Treinando o modelo de regressão...'})
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42, stratify=y)
    log_reg = LogisticRegression(random_state=42, class_weight='balanced', max_iter=1000)
    log_reg.fit(X_train, y_train)

    # --- 4. Avaliação e Predição ---
    y_pred_proba = log_reg.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= decision_threshold).astype(int)

    report = classification_report(y_test, y_pred, output_dict=True)
    auc = roc_auc_score(y_test, y_pred_proba)

    # --- 5. Interpretação ---
    coefs = pd.DataFrame(log_reg.coef_[0], index=X_train.columns, columns=['Coeficiente'])
    coefs['Chance (Odds Ratio)'] = np.exp(coefs['Coeficiente'])

    # --- 6. Geração do CSV de Saída ---
    df_orig_test = df_modelo_raw.loc[X_test.index].copy()
    df_orig_test.rename(columns={'MORTE': 'MORTE_REAL'}, inplace=True)
    df_orig_test['MORTE_PREDITA'] = y_pred
    df_orig_test['PROBABILIDADE_OBITO'] = y_pred_proba

    results_summary = {
        'classification_report': report,
        'auc': auc,
        'coefficients': coefs.to_dict()
    }

    return df_orig_test, results_summary, diagnostico_nome

@shared_task(bind=True)
def run_regressao_obitos_pipeline(self, ufs, anos, diagnostico_cids, comorbidade_cids, user_id, decision_threshold, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    RegressaoObitosTaskStatus = apps.get_model('pipeline_regressao_obitos', 'RegressaoObitosTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = RegressaoObitosTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED', 'message': 'Pipeline de Risco de Óbito iniciada.',
                'ufs': ufs, 'anos': anos, 'diagnostico_cids': diagnostico_cids,
                'comorbidade_cids': comorbidade_cids,
                'decision_threshold': decision_threshold
            }
        )
        self.update_state(state='PROGRESS', meta={'progress': 5, 'message': 'Iniciando coleta de dados...'})

        df_results, summary, diagnostico_nome = run_risk_analysis_logic(
            ufs, anos, diagnostico_cids, comorbidade_cids, decision_threshold, self
        )

        self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Salvando resultados...'})

        if output_filename and output_filename.strip():
            clean_name = output_filename.strip()
            if not clean_name.lower().endswith('.csv'):
                clean_name += '.csv'
            final_filename = secure_filename(clean_name)
        else:
            final_filename = f"risco_obito_{diagnostico_nome.lower()}_{task_id[:8]}.csv"

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "regressao_obitos"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / final_filename
        df_results.to_csv(output_path, index=False, sep=';', decimal=',')

        description_parts = [
            f"UFs: {', '.join(ufs)}",
            f"Anos: {', '.join(map(str, anos))}",
            f"Diagnóstico CIDs: {', '.join(diagnostico_cids)}"
        ]
        if comorbidade_cids:
            description_parts.append(f"Comorbidade CIDs: {', '.join(comorbidade_cids)}")

        description_parts.append(f"Limiar de Decisão: {decision_threshold}")
        description_parts.append(f"AUC: {summary['auc']:.4f}")

        description = ". ".join(description_parts) + "."

        relative_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
        output_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_path,
            filename=final_filename,
            description=description,
            file_type=FileType.LOGISTIC_REGRESSION
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Análise concluída com sucesso. AUC: {summary['auc']:.4f}"
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = summary
        task_status_entry.save()

        return {'status': 'SUCCESS', 'output_file_id': output_file.id, 'auc': summary['auc']}

    except Exception as e:
        logger.exception(f"Falha na pipeline de regressão de óbitos {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise
