# -*- coding: utf-8 -*-
"""
Pipeline Completo e Robusto de Machine Learning para Previsão de Risco de Readmissão Hospitalar.
Versão com engenharia de atributos aprimorada e sem features de comorbidade.
"""

# --- 1. Importação de Bibliotecas ---
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt

from pysus.online_data.SIH import SIH
from pysus.online_data.CNES import CNES
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score

# --- 2. CONFIGURAÇÕES GLOBAIS ---
UFS_PARA_ANALISE = ['TO']
ANOS_PARA_ANALISE = [2022, 2023]
FORCE_DOWNLOAD = False

DIR_BASE = Path('.')
DIR_DADOS_BRUTOS = DIR_BASE / 'dados_brutos'
DIR_DADOS_PROCESSADOS = DIR_BASE / 'dados_processados'
DIR_MODELOS = DIR_BASE / 'modelos'
DIR_OUTPUTS = DIR_BASE / 'outputs'

# --- 3. FUNÇÕES DO PIPELINE ---

def run_data_acquisition(ufs, anos, output_dir, force=False):
    # (Esta função permanece a mesma)
    print("="*80); print("ETAPA 1: Aquisição de Dados do DATASUS"); print("="*80)
    output_dir.mkdir(exist_ok=True)
    sih_path = output_dir / 'sih_raw_data.parquet'
    cnes_path = output_dir / 'cnes_st_raw_data.parquet'
    if not force and sih_path.exists() and cnes_path.exists():
        print("Arquivos de dados brutos já existem. Pulando download.")
        return
    print("\n--- Iniciando download dos dados do SIH ---"); sih_db = SIH(); print("Carregando índice de arquivos do SIH..."); sih_db.load(); print("Índice do SIH carregado.")
    all_sih_dfs = []
    for ano in anos:
        for uf in ufs:
            try:
                print(f"Buscando e baixando SIH para {uf}/{ano}..."); files = sih_db.get_files(group='RD', uf=uf, year=ano)
                if not files: print(f"  -> Nenhum arquivo encontrado para {uf}/{ano}."); continue
                downloaded = sih_db.download(files); df_ano_uf = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True); all_sih_dfs.append(df_ano_uf)
            except Exception as e: print(f"  AVISO: Erro ao processar SIH para {uf}/{ano}: {e}")
    if all_sih_dfs: df_sih_final = pd.concat(all_sih_dfs, ignore_index=True); df_sih_final.to_parquet(sih_path, index=False); print(f"\n✅ Dados do SIH consolidados e salvos em: {sih_path}")
    else: print("\n❌ Nenhum dado do SIH foi baixado. O pipeline não pode continuar."); exit()
    print("\n--- Iniciando download dos dados do CNES (Estabelecimentos) ---"); cnes_db = CNES(); print("Carregando índice de arquivos do CNES..."); cnes_db.load(); print("Índice do CNES carregado.")
    all_cnes_dfs = []
    for ano in anos:
        for uf in ufs:
            try:
                print(f"Buscando e baixando CNES para {uf}/{ano}-12..."); files = cnes_db.get_files(group='ST', uf=uf, year=ano, month=12)
                if not files: print(f"  -> Nenhum arquivo encontrado para {uf}/{ano}-12."); continue
                df_ano_uf = cnes_db.download(files).to_dataframe(); df_ano_uf['ANO'] = ano; all_cnes_dfs.append(df_ano_uf)
            except Exception as e: print(f"  AVISO: Erro ao processar CNES para {uf}/{ano}: {e}")
    if all_cnes_dfs: df_cnes_final = pd.concat(all_cnes_dfs, ignore_index=True); df_cnes_final.to_parquet(cnes_path, index=False); print(f"\n✅ Dados do CNES consolidados e salvos em: {cnes_path}")
    else: print("\n❌ Nenhum dado do CNES foi baixado. O pipeline não pode continuar."); exit()

def run_feature_engineering(raw_dir, processed_dir):
    """
    Etapa 2: Constrói o dataset analítico com features aprimoradas.
    """
    print("\n" + "="*80); print("ETAPA 2: Engenharia de Atributos Aprimorada"); print("="*80)
    processed_dir.mkdir(exist_ok=True)

    print("Carregando dados brutos..."); df_sih = pd.read_parquet(raw_dir / 'sih_raw_data.parquet'); df_cnes = pd.read_parquet(raw_dir / 'cnes_st_raw_data.parquet')

    print("1. Criando pseudo-ID e ordenando internações..."); df_sih['pseudo_id'] = df_sih['NASC'].astype(str) + '_' + df_sih['SEXO'].astype(str) + '_' + df_sih['MUNIC_RES'].astype(str)
    df_sih['DT_INTER'] = pd.to_datetime(df_sih['DT_INTER'], format='%Y%m%d', errors='coerce'); df_sih['DT_SAIDA'] = pd.to_datetime(df_sih['DT_SAIDA'], format='%Y%m%d', errors='coerce'); df_sih.dropna(subset=['DT_INTER', 'DT_SAIDA'], inplace=True); df_sih = df_sih.sort_values(by=['pseudo_id', 'DT_INTER'])

    print("2. Criando a variável alvo: 'foi_readmitido_em_30d'"); df_sih['proxima_internacao'] = df_sih.groupby('pseudo_id')['DT_INTER'].shift(-1); df_sih['dias_ate_readmissao'] = (df_sih['proxima_internacao'] - df_sih['DT_SAIDA']).dt.days; df_sih['foi_readmitido_em_30d'] = np.where((df_sih['dias_ate_readmissao'] >= 0) & (df_sih['dias_ate_readmissao'] <= 30), 1, 0)

    print("3. Construindo o DataFrame base de features a partir do SIH..."); df_sih_principal = df_sih[df_sih['IDENT'] == '1'].copy()

    print("4. Criando features aprimoradas...")
    features = pd.DataFrame(index=df_sih_principal.index)
    features['N_AIH'] = df_sih_principal['N_AIH']; features['foi_readmitido_em_30d'] = df_sih_principal['foi_readmitido_em_30d']

    features['IDADE'] = pd.to_numeric(df_sih_principal['IDADE'], errors='coerce')
    features['DIAS_PERM'] = pd.to_numeric(df_sih_principal['DIAS_PERM'], errors='coerce').fillna(0)

    features['USOU_UTI'] = np.where(pd.to_numeric(df_sih_principal['UTI_MES_TO'], errors='coerce').fillna(0) > 0, 1, 0)
    features['CAPITULO_CID'] = df_sih_principal['DIAG_PRINC'].str[0].astype('category')

    for col in ['SEXO', 'RACA_COR', 'CAR_INT']: features[col] = df_sih_principal[col].astype('category')

    print("5. Preparando e juntando dados do hospital (CNES)...")
    natureza_col = 'NAT_JUR' if 'NAT_JUR' in df_cnes.columns else 'NATUREZA'
    df_cnes_join = df_cnes[['CNES', 'ANO', natureza_col, 'LEITHOSP']].drop_duplicates(subset=['CNES', 'ANO']).copy()
    df_cnes_join['CNES'] = pd.to_numeric(df_cnes_join['CNES'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(7)
    df_cnes_join['ANO'] = df_cnes_join['ANO'].astype(int)

    df_sih_principal['ANO'] = df_sih_principal['DT_INTER'].dt.year
    df_sih_principal['CNES'] = pd.to_numeric(df_sih_principal['CNES'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(7)

    features = features.merge(df_sih_principal[['ANO', 'CNES']], left_index=True, right_index=True)
    features = features.merge(df_cnes_join, on=['CNES', 'ANO'], how='left')

    print("6. Limpando e tratando valores pós-junção...")
    features.rename(columns={natureza_col: 'HOSP_NATUREZA', 'LEITHOSP': 'HOSP_LEITOS'}, inplace=True)
    features['HOSP_NATUREZA'] = features['HOSP_NATUREZA'].astype('category')
    features['HOSP_LEITOS'] = pd.to_numeric(features['HOSP_LEITOS'], errors='coerce').fillna(0)

    features.drop(columns=['ANO', 'CNES'], inplace=True)

    features.dropna(subset=['IDADE'], inplace=True)

    print("7. Salvando dataset final...")
    output_path = processed_dir / 'analytical_dataset_readmission.parquet'; features.to_parquet(output_path, index=False)
    print(f"\n✅ Dataset analítico criado e salvo em: {output_path}")
    print(f"\nDistribuição da variável alvo:"); print(features['foi_readmitido_em_30d'].value_counts(normalize=True))

def run_model_training(processed_dir, models_dir):
    # (Esta função permanece a mesma)
    print("\n" + "="*80); print("ETAPA 3: Treinamento do Modelo"); print("="*80)
    models_dir.mkdir(exist_ok=True)
    print("Carregando dataset analítico..."); df = pd.read_parquet(processed_dir / 'analytical_dataset_readmission.parquet')
    print("Preparando dados para o treinamento..."); y = df['foi_readmitido_em_30d']; X = df.drop(columns=['N_AIH', 'foi_readmitido_em_30d'])
    for col in X.select_dtypes(include=['object']).columns: X[col] = X[col].astype('category')
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    print("Treinando o modelo LightGBM..."); model = lgb.LGBMClassifier(objective='binary', class_weight='balanced', random_state=42)
    model.fit(X_train, y_train, categorical_feature='auto')
    print("\n--- Avaliando o modelo nos dados de teste ---"); y_pred = model.predict(X_test); y_pred_proba = model.predict_proba(X_test)[:, 1]
    print("\nRelatório de Classificação:"); print(classification_report(y_test, y_pred, zero_division=0))
    auc = roc_auc_score(y_test, y_pred_proba); auprc = average_precision_score(y_test, y_pred_proba)
    print(f"Área sob a Curva ROC (AUC): {auc:.4f}"); print(f"Área sob a Curva de Precisão-Recall (AUPRC): {auprc:.4f}")
    model_path = models_dir / 'lgbm_readmission_model.joblib'; joblib.dump(model, model_path); print(f"\n✅ Modelo treinado salvo em: {model_path}")
    X_test.to_parquet(processed_dir / 'X_test.parquet'); y_test.to_frame().to_parquet(processed_dir / 'y_test.parquet')

def run_model_interpretation(processed_dir, models_dir, outputs_dir):
    # (Esta função permanece a mesma, com mapa de nomes atualizado)
    print("\n" + "="*80); print("ETAPA 4: Interpretação do Modelo (IA Explicável com SHAP)"); print("="*80)
    outputs_dir.mkdir(exist_ok=True)
    print("Carregando modelo e dados de teste..."); model = joblib.load(models_dir / 'lgbm_readmission_model.joblib'); X_test = pd.read_parquet(processed_dir / 'X_test.parquet')

    # --- CORREÇÃO APLICADA AQUI ---
    feature_name_map = {
        'IDADE': 'Idade', 'DIAS_PERM': 'Dias de Permanência',
        'USOU_UTI': 'Utilizou UTI', 'CAPITULO_CID': 'Grupo do Diagnóstico',
        'SEXO': 'Sexo', 'RACA_COR': 'Raça/Cor', 'CAR_INT': 'Caráter da Internação',
        'HOSP_NATUREZA': 'Natureza do Hospital', 'HOSP_LEITOS': 'Nº de Leitos do Hospital'
    }

    X_test_renamed = X_test.rename(columns=feature_name_map)
    print("Calculando valores SHAP..."); explainer = shap.TreeExplainer(model); shap_values = explainer.shap_values(X_test)
    if isinstance(shap_values, list): shap_values_risk = shap_values[1]
    else: shap_values_risk = shap_values
    if isinstance(explainer.expected_value, list): base_value = explainer.expected_value[1]
    else: base_value = explainer.expected_value
    print("1. Gerando gráfico de importância global (Summary Plot)..."); fig, ax = plt.subplots(figsize=(10, 8)); shap.summary_plot(shap_values_risk, X_test_renamed, plot_type="bar", max_display=15, show=False); plt.title("Importância Média dos Atributos para o Risco de Readmissão"); plt.tight_layout(); summary_path = outputs_dir / 'shap_summary_plot_friendly.png'; plt.savefig(summary_path, dpi=150); plt.close(); print(f"  -> Gráfico salvo em: {summary_path}")
    print("\n2. Gerando explicação para um caso individual de alto risco..."); y_pred_proba = model.predict_proba(X_test)[:, 1]; high_risk_index = np.argmax(y_pred_proba); print(f"  -> Analisando o paciente no índice {high_risk_index} do conjunto de teste."); fig, ax = plt.subplots(figsize=(10, 8))
    shap.waterfall_plot(shap.Explanation(values=shap_values_risk[high_risk_index], base_values=base_value, data=X_test_renamed.iloc[high_risk_index]), max_display=15, show=False); plt.tight_layout(); waterfall_path = outputs_dir / 'shap_waterfall_plot_individual_friendly.png'; plt.savefig(waterfall_path, dpi=150); plt.close(); print(f"  -> Gráfico Waterfall salvo em: {waterfall_path}"); print("\n✅ Análise de Interpretabilidade concluída.")

# --- 4. BLOCO PRINCIPAL DE ORQUESTRAÇÃO ---
if __name__ == "__main__":
    print("🚀 INICIANDO PIPELINE DE PREVISÃO DE RISCO DE READMISSÃO 🚀")
    for d in [DIR_DADOS_BRUTOS, DIR_DADOS_PROCESSADOS, DIR_MODELOS, DIR_OUTPUTS]: d.mkdir(exist_ok=True)
    run_data_acquisition(UFS_PARA_ANALISE, ANOS_PARA_ANALISE, DIR_DADOS_BRUTOS, force=FORCE_DOWNLOAD)
    run_feature_engineering(DIR_DADOS_BRUTOS, DIR_DADOS_PROCESSADOS)
    run_model_training(DIR_DADOS_PROCESSADOS, DIR_MODELOS)
    run_model_interpretation(DIR_DADOS_PROCESSADOS, DIR_MODELOS, DIR_OUTPUTS)
    print("\n" + "="*80); print("🎉 PIPELINE CONCLÚİDO COM SUCESSO! 🎉"); print("="*80)
