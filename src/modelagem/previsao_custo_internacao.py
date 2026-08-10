# -*- coding: utf-8 -*-
"""
======================================================================
  MODELO PREDITIVO DE CUSTO DE INTERNAÇÃO HOSPITALAR (REGRESSÃO)
======================================================================
Este script treina um modelo de Machine Learning (LightGBM Regressor)
para prever o custo total (VAL_TOT) de uma internação hospitalar com
base em características do paciente, da internação e do hospital.

O pipeline inclui:
1. Carregamento de dados do SIH e CNES.
2. Junção das bases e engenharia de features.
3. Tratamento da variável alvo (custo) com transformação logarítmica.
4. Treinamento e avaliação do modelo com métricas de regressão.
5. Análise de interpretabilidade com SHAP para identificar os drivers de custo.
6. Salvamento do modelo e dos dados de treino para uso em produção.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import joblib
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# Importações do PySUS
from pysus.online_data.SIH import SIH
from pysus.online_data.CNES import CNES

# Ferramentas de Machine Learning
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import lightgbm as lgb


def carregar_dados(ufs: list, anos: list):
    """Carrega dados de internações (SIH) e estabelecimentos (CNES)."""
    print(f"\n--- [ETAPA 1] Carregando dados para {ufs}/{anos} ---")
    df_sih, df_cnes = pd.DataFrame(), pd.DataFrame()
    try:
        print(f"[LOG] Carregando SIH..."); sih_db = SIH(); sih_db.load()
        files_sih = sih_db.get_files(group='RD', uf=ufs, year=anos)
        if files_sih:
            downloaded_sih = sih_db.download(files_sih)
            if isinstance(downloaded_sih, list): df_sih = pd.concat([f.to_dataframe() for f in downloaded_sih], ignore_index=True)
            elif hasattr(downloaded_sih, "to_dataframe"): df_sih = downloaded_sih.to_dataframe()
    except Exception as e: print(f"❌ Erro ao carregar SIH: {e}"); return None, None
    try:
        print(f"[LOG] Carregando CNES..."); cnes_db = CNES(); cnes_db.load()
        dfs_cnes_ano = []
        for ano in anos:
            files_cnes = cnes_db.get_files(group='ST', uf=ufs, year=ano, month=12)
            if files_cnes:
                downloaded_cnes = cnes_db.download(files_cnes)
                if isinstance(downloaded_cnes, list): df_ano = pd.concat([f.to_dataframe() for f in downloaded_cnes], ignore_index=True)
                elif hasattr(downloaded_cnes, "to_dataframe"): df_ano = downloaded_cnes.to_dataframe()
                df_ano['ANO_COMPETENCIA_CNES'] = ano
                dfs_cnes_ano.append(df_ano)
        if dfs_cnes_ano: df_cnes = pd.concat(dfs_cnes_ano, ignore_index=True)
    except Exception as e: print(f"❌ Erro ao carregar CNES: {e}"); return None, None
    print("✅ Bases de dados carregadas com sucesso."); return df_sih, df_cnes

def preparar_dados(df_sih: pd.DataFrame, df_cnes: pd.DataFrame):
    """Prepara o dataset para a modelagem de regressão."""
    print("\n--- [ETAPA 2] Preparação e Engenharia de Features ---")
    df_sih['ANO_CMPT'] = pd.to_numeric(df_sih['ANO_CMPT'], errors='coerce')
    df_sih['CNES'] = pd.to_numeric(df_sih['CNES'], errors='coerce').astype('Int64').astype(str)
    df_cnes['CNES'] = pd.to_numeric(df_cnes['CNES'], errors='coerce').astype('Int64').astype(str)
    df = pd.merge(df_sih, df_cnes, left_on=['CNES', 'ANO_CMPT'], right_on=['CNES', 'ANO_COMPETENCIA_CNES'], how='left')
    print(f"[LOG] SIH e CNES unificados. Shape inicial: {df.shape}")
    features = ['VAL_TOT', 'DIAG_PRINC', 'PROC_REA', 'DIAS_PERM', 'IDADE', 'SEXO', 'CAR_INT', 'UTI_MES_TO', 'MORTE', 'TP_UNID', 'NAT_JUR', 'LEITHOSP', 'ATIVIDAD']
    df_modelo = df[[col for col in features if col in df.columns]].copy()
    numeric_cols = ['VAL_TOT', 'DIAS_PERM', 'IDADE', 'UTI_MES_TO', 'LEITHOSP']
    for col in numeric_cols: df_modelo[col] = pd.to_numeric(df_modelo[col], errors='coerce')
    df_modelo.dropna(subset=numeric_cols, inplace=True)
    df_modelo = df_modelo[df_modelo['VAL_TOT'] > 0].copy()
    df_modelo['VAL_TOT_LOG'] = np.log1p(df_modelo['VAL_TOT'])
    categorical_cols = ['DIAG_PRINC', 'PROC_REA', 'SEXO', 'CAR_INT', 'TP_UNID', 'NAT_JUR', 'ATIVIDAD', 'MORTE']
    for col in categorical_cols:
        if col in df_modelo.columns: df_modelo[col] = df_modelo[col].astype(str).astype('category')
    print(f"✅ Dados preparados. Shape final para modelagem: {df_modelo.shape}")
    return df_modelo


def treinar_e_avaliar_modelo(df: pd.DataFrame, dir_saida: Path):
    """Treina um modelo de regressão, avalia, interpreta e salva os artefatos."""
    print("\n--- [ETAPA 3 & 4] Treinamento, Avaliação e Interpretação do Modelo ---")
    dir_saida.mkdir(parents=True, exist_ok=True)

    y = df['VAL_TOT_LOG']
    X = df.drop(columns=['VAL_TOT', 'VAL_TOT_LOG'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    modelo = lgb.LGBMRegressor(random_state=42, n_jobs=-1)
    print("[LOG] Treinando o modelo LightGBM Regressor...")
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")

    y_pred_log = modelo.predict(X_test)
    y_test_orig = np.expm1(y_test)
    y_pred_orig = np.expm1(y_pred_log)

    mse = mean_squared_error(y_test_orig, y_pred_orig)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test_orig, y_pred_orig)

    print("\n--- Performance do Modelo no Conjunto de Teste ---")
    print(f"RMSE (Raiz do Erro Quadrático Médio): R$ {rmse:.2f}")
    print(f"R² (Coeficiente de Determinação): {r2:.4f}")

    feature_name_map = {
        'DIAG_PRINC': 'Diagnóstico Principal (CID-10)','PROC_REA': 'Procedimento Realizado (SIGTAP)','DIAS_PERM': 'Dias de Permanência',
        'IDADE': 'Idade do Paciente','SEXO': 'Sexo','CAR_INT': 'Caráter da Internação','UTI_MES_TO': 'Total de Diárias de UTI',
        'MORTE': 'Desfecho Óbito','TP_UNID': 'Tipo de Unidade Hospitalar','NAT_JUR': 'Natureza Jurídica do Hospital',
        'LEITHOSP': 'Nº Total de Leitos do Hospital','ATIVIDAD': 'Hospital de Ensino/Pesquisa'
    }
    X_test_renamed = X_test.rename(columns=feature_name_map)

    print("\n[LOG] Calculando os valores SHAP...")
    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)

    plt.figure()
    shap.summary_plot(shap_values, X_test_renamed, show=False)
    plt.title("Fatores que Influenciam o Custo da Internação (SHAP)", fontsize=16)
    plt.tight_layout()
    caminho_shap = dir_saida / "shap_custo_internacao_friendly.png"
    plt.savefig(caminho_shap)
    plt.close()
    print(f"📈 Gráfico SHAP de fatores de custo salvo em: {caminho_shap}")

    caminho_modelo = dir_saida / "modelo_custo_internacao.joblib"
    joblib.dump(modelo, caminho_modelo)
    print(f"💾 Modelo de previsão de custo salvo em: {caminho_modelo}")

    # --- ADIÇÃO IMPORTANTE ---
    # Salva o DataFrame X_train, que contém o schema (colunas, tipos, categorias)
    # necessário para o script de previsão.
    caminho_dados_treino = dir_saida / "X_train_data.parquet"
    X_train.to_parquet(caminho_dados_treino)
    print(f"💾 Dados de treino (para SHAP) salvos em: {caminho_dados_treino}")
    # --- FIM DA ADIÇÃO ---


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo para prever o custo de internações hospitalares.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2023], help="Anos de dados históricos a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsao_custo", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    df_sih_raw, df_cnes_raw = carregar_dados(ufs=args.ufs, anos=args.anos)

    if df_sih_raw is not None and not df_sih_raw.empty and df_cnes_raw is not None and not df_cnes_raw.empty:
        df_pronto = preparar_dados(df_sih_raw, df_cnes_raw)
        if not df_pronto.empty:
            treinar_e_avaliar_modelo(df_pronto, Path(args.dir_saida))
            print("\n" + "="*80)
            print("🎉 PIPELINE DE PREVISÃO DE CUSTO CONCLUÍDO! 🎉")
            print("="*80)
