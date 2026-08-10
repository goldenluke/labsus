# -*- coding: utf-8 -*-
"""
======================================================================
  MODELO DE CLASSIFICAÇÃO PARA RISCO DE READMISSÃO HOSPITALAR EM 90 DIAS
======================================================================
Versão otimizada para lidar com grandes volumes de dados em ambientes
com memória limitada e com carregamento de dados robusto.
"""

import pandas as pd
from pathlib import Path
import argparse
import numpy as np

# Importações do PySUS
from pysus.online_data.SIH import SIH
from pysus.online_data.CNES import CNES

# Ferramentas de Machine Learning
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import matplotlib.pyplot as plt
import seaborn as sns

def otimizar_memoria(df: pd.DataFrame) -> pd.DataFrame:
    memoria_antes = df.memory_usage(deep=True).sum() / 1024**2
    for col in df.columns:
        df_col = pd.to_numeric(df[col], errors='coerce')
        if not df_col.isnull().all():
            col_type = df_col.dtype
            if 'int' in str(col_type):
                c_min, c_max = df_col.min(), df_col.max()
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max: df[col] = df_col.astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max: df[col] = df_col.astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max: df[col] = df_col.astype(np.int32)
                else: df[col] = df_col.astype(np.int64)
            elif 'float' in str(col_type):
                c_min, c_max = df_col.min(), df_col.max()
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max: df[col] = df_col.astype(np.float32)
                else: df[col] = df_col.astype(np.float64)
    memoria_depois = df.memory_usage(deep=True).sum() / 1024**2
    print(f"  -> Memória otimizada: {memoria_antes:.2f} MB -> {memoria_depois:.2f} MB")
    return df

def carregar_e_preparar_dados(ufs: list, anos: list):
    """
    Carrega e prepara os dados de forma otimizada.
    """
    print(f"\n--- [ETAPA 1] Carregando e preparando dados para {ufs}/{anos} ---")

    def _download_and_concat(db_instance, files_list):
        if not files_list: return pd.DataFrame()
        downloaded_items = db_instance.download(files_list)
        if isinstance(downloaded_items, list):
            return pd.concat([item.to_dataframe() for item in downloaded_items if hasattr(item, 'to_dataframe')], ignore_index=True)
        elif hasattr(downloaded_items, 'to_dataframe'):
            return downloaded_items.to_dataframe()
        return pd.DataFrame()

    sih_db = SIH().load()
    dfs_sih = []
    print("[LOG] Carregando e otimizando SIH ano a ano...")
    for ano in anos:
        try:
            files_sih = sih_db.get_files(group='RD', uf=ufs, year=ano)
            if files_sih:
                df_ano = _download_and_concat(sih_db, files_sih)
                if not df_ano.empty: dfs_sih.append(otimizar_memoria(df_ano))
        except Exception as e:
            print(f"  -> Aviso: Falha ao carregar SIH para o ano {ano}: {e}")
    if not dfs_sih: print("❌ Erro: Nenhum dado do SIH pôde ser carregado."); return None
    df_sih = pd.concat(dfs_sih, ignore_index=True)

    cnes_db = CNES().load()
    dfs_cnes = []
    print("[LOG] Carregando e otimizando CNES ano a ano...")
    for ano in anos:
        try:
            files_cnes = cnes_db.get_files(group='ST', uf=ufs, year=ano, month=12)
            if files_cnes:
                df_ano = _download_and_concat(cnes_db, files_cnes)
                if not df_ano.empty:
                    df_ano['ANO_COMPETENCIA_CNES'] = ano
                    dfs_cnes.append(otimizar_memoria(df_ano))
        except Exception as e:
            print(f"  -> Aviso: Falha ao carregar CNES para o ano {ano}: {e}")
    if not dfs_cnes: print("❌ Erro: Nenhum dado do CNES pôde ser carregado."); return None
    df_cnes = pd.concat(dfs_cnes, ignore_index=True)

    print("[LOG] Preparando dados para análise...")

    df_sih['pseudo_id'] = df_sih['NASC'].astype(str) + '_' + df_sih['SEXO'].astype(str) + '_' + df_sih['MUNIC_RES'].astype(str)
    df_sih['DT_INTER'] = pd.to_datetime(df_sih['DT_INTER'], format='%Y%m%d', errors='coerce')
    df_sih['DT_SAIDA'] = pd.to_datetime(df_sih['DT_SAIDA'], format='%Y%m%d', errors='coerce')
    df_sih.dropna(subset=['DT_INTER', 'DT_SAIDA'], inplace=True)
    df_sih = df_sih.sort_values(by=['pseudo_id', 'DT_INTER'])
    df_sih['proxima_internacao'] = df_sih.groupby('pseudo_id')['DT_INTER'].shift(-1)
    df_sih['dias_ate_readmissao'] = (df_sih['proxima_internacao'] - df_sih['DT_SAIDA']).dt.days

    df_sih['ALVO_READMITIDO_90D'] = np.where(
        (df_sih['dias_ate_readmissao'] >= 0) & (df_sih['dias_ate_readmissao'] <= 90), 1, 0
    )
    data_fim_estudo = pd.to_datetime(f"{max(anos)}-12-31")
    df_sih['dias_de_observacao'] = (data_fim_estudo - df_sih['DT_SAIDA']).dt.days
    df_sih_modelo = df_sih[
        (df_sih['ALVO_READMITIDO_90D'] == 1) |
        ((df_sih['ALVO_READMITIDO_90D'] == 0) & (df_sih['dias_de_observacao'] >= 90))
    ].copy()

    df_sih_modelo['ANO_CMPT'] = df_sih_modelo['DT_INTER'].dt.year
    df_sih_modelo['CNES'] = pd.to_numeric(df_sih_modelo['CNES'], errors='coerce').astype('Int64').astype(str)
    df_cnes['CNES'] = pd.to_numeric(df_cnes['CNES'], errors='coerce').astype('Int64').astype(str)
    df = pd.merge(df_sih_modelo, df_cnes,
                  left_on=['CNES', 'ANO_CMPT'],
                  right_on=['CNES', 'ANO_COMPETENCIA_CNES'],
                  how='left')

    features_modelo = [
        'ALVO_READMITIDO_90D', 'IDADE', 'SEXO', 'DIAS_PERM',
        'UTI_MES_TO', 'DIAG_PRINC', 'LEITHOSP', 'ATIVIDAD'
    ]
    df_final = df[[col for col in features_modelo if col in df.columns]].copy()
    for col in ['IDADE', 'DIAS_PERM', 'UTI_MES_TO', 'LEITHOSP']:
        df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
    df_final.dropna(inplace=True)

    print(f"✅ Dados preparados com {len(df_final)} internações válidas para a análise.")
    return df_final

def treinar_e_interpretar_modelo(df: pd.DataFrame, dir_saida: Path):
    """Treina um modelo de classificação, avalia e gera um gráfico de importância."""
    print("\n--- [ETAPA 2] Treinando e Interpretando o Modelo de Classificação ---")
    dir_saida.mkdir(parents=True, exist_ok=True)

    y = df['ALVO_READMITIDO_90D']
    X = df.drop(columns=['ALVO_READMITIDO_90D'])

    for col in ['SEXO', 'DIAG_PRINC', 'ATIVIDAD']:
        if col in X.columns: X[col] = X[col].astype('category')

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    if y_train.nunique() < 2:
        print("❌ Erro: O conjunto de treino contém apenas uma classe.")
        return

    ratio = y_train.value_counts()[0] / y_train.value_counts()[1] if y_train.value_counts().get(1, 0) > 0 else 1
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)

    print("[LOG] Treinando o modelo LightGBM...")
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")

    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n--- Performance do Modelo --- \nÁrea sob a Curva ROC (AUC): {auc:.4f}")

    # ==========================================================
    # --- ANÁLISE SHAP REMOVIDA ---
    # --- NOVA ANÁLISE DE IMPORTÂNCIA DE FEATURES (LightGBM) ---
    # ==========================================================
    print("\n[LOG] Gerando gráfico de importância de features...")

    importances = pd.DataFrame({
        'feature': X.columns,
        'importance': modelo.feature_importances_
    }).sort_values('importance', ascending=False)

    plt.figure(figsize=(10, 8))
    sns.barplot(x='importance', y='feature', data=importances)
    plt.title("Importância dos Fatores para Readmissão em 90 Dias")
    plt.tight_layout()
    caminho_fig = dir_saida / "feature_importance_readmissao_90d.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de importância de features salvo em: {caminho_fig}")
    # ==========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo para prever o risco de readmissão em 90 dias.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022, 2023], help="Anos de dados históricos a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_readmissao_90d", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    df_final = carregar_e_preparar_dados(ufs=args.ufs, anos=args.anos)

    if df_final is not None and not df_final.empty:
        treinar_e_interpretar_modelo(df_final, Path(args.dir_saida))
        print("\n" + "="*80)
        print("🎉 PIPELINE DE CLASSIFICAÇÃO DE RISCO CONCLUÍDO! 🎉")
        print("="*80)
