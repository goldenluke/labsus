# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE AVANÇADA DE SOBREVIDA INFANTIL E FATORES DE RISCO
======================================================================
Este script implementa um pipeline de Machine Learning aprimorado para
investigar os fatores de risco para a mortalidade infantil.
"""

import pandas as pd
from pathlib import Path
import argparse
import os

from pysus.online_data.SINASC import download as download_sinasc
from pysus.online_data.SIM import download as download_sim
from pysus.online_data.CNES import download as download_cnes

import recordlinkage
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import joblib
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# Supondo que a função filtrar_populacao está em src/utils/dataloaders.py
try:
    from src.utils.dataloaders import filtrar_populacao
except (ModuleNotFoundError, ImportError):
    # (código da função de fallback omitido para brevidade)
    pass

def carregar_dados(ufs: list, ano_coorte: int):
    # (Esta função permanece a mesma da versão anterior, sem alterações)
    print(f"\n--- [ETAPA 1] Carregando dados para a coorte de {ano_coorte} em {ufs} ---")
    df_sinasc, df_sim, df_cnes = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        print(f"[LOG] Carregando SINASC para {ufs}/{ano_coorte}..."); downloaded_data = download_sinasc(states=ufs, years=ano_coorte, groups=['DN'])
        if downloaded_data:
            if isinstance(downloaded_data, list): df_sinasc = pd.concat([f.to_dataframe() for f in downloaded_data], ignore_index=True)
            else: df_sinasc = downloaded_data.to_dataframe()
    except Exception as e: print(f"❌ Erro ao carregar SINASC: {e}"); return None, None, None
    anos_sim = [ano_coorte, ano_coorte + 1]; dfs_sim = []
    try:
        print(f"[LOG] Carregando SIM para {ufs}/{anos_sim}...");
        for ano in anos_sim:
            downloaded_data = download_sim(states=ufs, years=ano, groups=['CID10'])
            if downloaded_data:
                if isinstance(downloaded_data, list): df_ano = pd.concat([f.to_dataframe() for f in downloaded_data], ignore_index=True)
                else: df_ano = downloaded_data.to_dataframe()
                dfs_sim.append(df_ano)
        if dfs_sim: df_sim = pd.concat(dfs_sim, ignore_index=True)
    except Exception as e: print(f"❌ Erro ao carregar SIM: {e}"); return None, None, None
    try:
        print(f"[LOG] Carregando CNES para {ufs}/{ano_coorte}..."); downloaded_data = download_cnes(group='ST', states=ufs, years=ano_coorte, months=12)
        if downloaded_data:
            if isinstance(downloaded_data, list): df_cnes = pd.concat([f.to_dataframe() for f in downloaded_data], ignore_index=True)
            else: df_cnes = downloaded_data.to_dataframe()
    except Exception as e: print(f"❌ Erro ao carregar CNES: {e}"); return None, None, None
    print("✅ Todas as bases de dados foram carregadas com sucesso.")
    return df_sinasc, df_sim, df_cnes

def vincular_obitos_real(df_sinasc: pd.DataFrame, df_sim: pd.DataFrame):
    # (Esta função permanece a mesma da versão anterior, sem alterações)
    print("\n--- [ETAPA 2] Vinculando nascimentos e óbitos (Linkage Real) ---")
    if df_sim is None or df_sim.empty: df_sinasc['OBITO_INFANTIL'] = 0; return df_sinasc
    df_sim_infantil = df_sim[pd.to_numeric(df_sim['IDADE'], errors='coerce') < 401].copy()
    if df_sim_infantil.empty: df_sinasc['OBITO_INFANTIL'] = 0; return df_sinasc
    df_nasc = df_sinasc[['CODMUNRES', 'DTNASC']].reset_index().rename(columns={'index': 'rec_id_nasc'}); df_obit = df_sim_infantil[['CODMUNRES', 'DTNASC']].reset_index().rename(columns={'index': 'rec_id_obit'})
    df_nasc.set_index('rec_id_nasc', inplace=True); df_obit.set_index('rec_id_obit', inplace=True)
    indexer = recordlinkage.Index(); indexer.block('CODMUNRES'); candidate_links = indexer.index(df_nasc, df_obit)
    if len(candidate_links) == 0: df_sinasc['OBITO_INFANTIL'] = 0; return df_sinasc
    compare_cls = recordlinkage.Compare(); compare_cls.exact('DTNASC', 'DTNASC', label='DTNASC'); features = compare_cls.compute(candidate_links, df_nasc, df_obit)
    matches = features[features.sum(axis=1) >= 1]
    rec_ids_nasc_com_obito = matches.index.get_level_values(0)
    df_sinasc['OBITO_INFANTIL'] = 0; df_sinasc.loc[rec_ids_nasc_com_obito, 'OBITO_INFANTIL'] = 1
    print(f"Distribuição do alvo 'OBITO_INFANTIL':\n{df_sinasc['OBITO_INFANTIL'].value_counts(normalize=True)}")
    return df_sinasc



# ... (imports e outras funções permanecem os mesmos) ...

def enriquecer_com_cnes(df_vinculado: pd.DataFrame, df_cnes: pd.DataFrame):
    """Enriquece os dados de nascimento com informações do hospital (CNES)."""
    print("\n--- [ETAPA 3] Enriquecendo dados com informações do CNES ---")
    if df_cnes is None or df_cnes.empty:
        df_vinculado['QTLEIT39'] = 0
        df_vinculado['ATIVIDAD'] = 'N/A'
        df_vinculado['VINC_SUS'] = 'N/A' # Adiciona a coluna mesmo se o CNES falhar
        return df_vinculado

    # ==========================================================
    # --- ALTERAÇÃO APLICADA AQUI ---
    # Adiciona 'VINC_SUS' à lista de features a serem extraídas do CNES
    features_cnes = ['CNES', 'TP_UNID', 'ATIVIDAD', 'LEITHOSP', 'QTLEIT39', 'VINC_SUS']
    # ==========================================================

    df_cnes_slim = df_cnes[[col for col in features_cnes if col in df_cnes.columns]].copy()
    df_vinculado['CODESTAB'] = pd.to_numeric(df_vinculado['CODESTAB'], errors='coerce').astype('Int64').astype(str)
    df_cnes_slim['CNES'] = pd.to_numeric(df_cnes_slim['CNES'], errors='coerce').astype('Int64').astype(str)

    df_enriquecido = pd.merge(df_vinculado, df_cnes_slim, left_on='CODESTAB', right_on='CNES', how='left')

    # Preenche valores nulos para as colunas do CNES
    df_enriquecido['QTLEIT39'] = df_enriquecido['QTLEIT39'].fillna(0)
    df_enriquecido['VINC_SUS'] = df_enriquecido['VINC_SUS'].fillna('Ignorado')

    print("✅ Dados enriquecidos com sucesso.")
    return df_enriquecido

def preparar_dados_para_modelo(df: pd.DataFrame):
    # (Esta função permanece a mesma da versão anterior, sem alterações)
    print("\n--- [ETAPA 4] Preparando dados para o modelo de sobrevida ---")
    features_finais = ['PESO', 'GESTACAO', 'APGAR5', 'IDADEMAE', 'ESCMAE2010', 'CONSPRENAT', 'QTDFILVIVO', 'QTDFILMORT', 'PARTO', 'RACACORMAE', 'QTLEIT39', 'ATIVIDAD']
    df_modelo = df[[col for col in features_finais if col in df.columns] + ['OBITO_INFANTIL']].copy()
    for col in features_finais:
        if col in df_modelo.columns: df_modelo[col] = pd.to_numeric(df_modelo[col], errors='coerce')
    colunas_para_limpeza = [col for col in features_finais if col in df_modelo.columns]
    initial_rows = len(df_modelo); df_limpo = df_modelo.dropna(subset=colunas_para_limpeza); print(f"[LOG] {initial_rows - len(df_limpo)} registros removidos.")
    y = df_limpo['OBITO_INFANTIL']; X = df_limpo.drop(columns=['OBITO_INFANTIL'])
    print(f"✅ Dados preparados. Features (X) shape: {X.shape}, Alvo (y) shape: {y.shape}")
    return X, y

def treinar_e_avaliar_modelo_obito(X: pd.DataFrame, y: pd.Series, dir_saida: Path):
    """
    Treina o modelo de risco de óbito e gera gráficos de interpretação com SHAP.
    """
    print("\n--- [ETAPA 5] Treinamento, Avaliação e Interpretação do Modelo ---")
    dir_saida.mkdir(parents=True, exist_ok=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    if y_train.value_counts().get(1, 0) == 0:
        print("❌ Erro: Não há amostras da classe minoritária no treino."); return
    ratio = y_train.value_counts()[0] / y_train.value_counts()[1]
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n--- Performance do Modelo --- \nÁrea sob a Curva ROC (AUC): {auc:.4f}")

    # --- REINTEGRAÇÃO DA INTERPRETABILIDADE COM SHAP ---
    print("\n[LOG] Calculando e salvando a interpretação do modelo com SHAP...")

    feature_name_map = {
        'PESO': 'Peso ao Nascer (g)', 'GESTACAO': 'Semanas de Gestação (Faixa)', 'APGAR5': 'Índice de Apgar (5º Minuto)',
        'IDADEMAE': 'Idade da Mãe', 'ESCMAE2010': 'Escolaridade da Mãe', 'CONSPRENAT': 'Nº de Consultas Pré-Natal',
        'QTDFILVIVO': 'Nº de Filhos Vivos Anteriores', 'QTDFILMORT': 'Nº de Filhos Mortos Anteriores',
        'PARTO': 'Tipo de Parto', 'RACACORMAE': 'Raça/Cor da Mãe',
        'QTLEIT39': 'Nº de Leitos de UTI Neonatal no Hospital', 'ATIVIDAD': 'Hospital de Ensino/Pesquisa'
    }
    X_test_renamed = X_test.rename(columns=feature_name_map)

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)

    if isinstance(shap_values, list): shap_values_risk = shap_values[1]
    else: shap_values_risk = shap_values

    plt.figure()
    shap.summary_plot(shap_values_risk, X_test_renamed, plot_type="bar", show=False)
    plt.title('Importância dos Fatores para Previsão de Óbito Infantil (SHAP)', fontsize=16)
    plt.tight_layout()
    caminho_fig = dir_saida / "shap_feature_importance_obito.png"
    plt.savefig(caminho_fig, dpi=150)
    plt.close()
    print(f"\n📈 Gráfico de importância SHAP salvo em: {caminho_fig}")

        # ==========================================================
    # --- ADIÇÃO PARA SALVAR O MODELO ---
    # ==========================================================
    caminho_modelo = dir_saida / "modelo_sobrevida_infantil.joblib"
    joblib.dump(modelo, caminho_modelo)
    print(f"💾 Modelo de previsão de sobrevida salvo em: {caminho_modelo}")
    # ==========================================================
    # --- FIM DA REINTEGRAÇÃO ---

def main(args):
    """
    Função principal que orquestra todo o pipeline.
    """
    df_sinasc, df_sim, df_cnes = carregar_dados(ufs=args.ufs, ano_coorte=args.ano)

    if df_sinasc is not None and not df_sinasc.empty:
        df_vinculado = vincular_obitos_real(df_sinasc, df_sim)
        if df_vinculado is not None:
            df_enriquecido = enriquecer_com_cnes(df_vinculado, df_cnes)
            if df_enriquecido is not None:
                print("\n--- Adicionando dados de população ao painel de sobrevida ---")
                dfs_pop = [
                    df_pop_uf for df_pop_uf in (
                        filtrar_populacao(arquivo_populacao=Path(args.pop), uf=uf, ano=args.ano)
                        for uf in args.ufs
                    ) if df_pop_uf is not None
                ]
                df_pop = pd.concat(dfs_pop) if dfs_pop else None
                df_final_com_pop = df_enriquecido.copy()
                if df_pop is not None:
                    df_final_com_pop['CODMUNRES_6DIG'] = df_final_com_pop['CODMUNRES'].astype(str).str[:6]
                    df_final_com_pop = pd.merge(df_final_com_pop, df_pop[['populacao', 'UF']], left_on='CODMUNRES_6DIG', right_index=True, how='left')
                    print("✅ População adicionada com sucesso.")
                else:
                    print("⚠️ Não foi possível carregar os dados de população.")
                    df_final_com_pop['populacao'] = None

                if 'UF' not in df_final_com_pop.columns:
                    df_final_com_pop['UF'] = args.ufs[0].upper() if len(args.ufs) == 1 else None

                output_dir = Path(args.dir_saida)
                output_dir.mkdir(parents=True, exist_ok=True)
                ufs_str = '-'.join(args.ufs).lower()
                nome_arquivo = f"painel_sobrevida_infantil_{ufs_str}_{args.ano}.csv"
                caminho_csv = output_dir / nome_arquivo
                df_final_com_pop.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
                print(f"\n📄 Painel de dados final (com população e UF) salvo em: '{caminho_csv}'")

                X, y = preparar_dados_para_modelo(df_final_com_pop)
                if not X.empty and y.nunique() > 1:
                    treinar_e_avaliar_modelo_obito(X, y, Path(args.dir_saida))
                    print("\n" + "="*80)
                    print("🎉 PIPELINE DE ANÁLISE DE SOBREVIDA CONCLUÍDO! 🎉")
                    print("="*80)
                else:
                    print("Dados insuficientes para treinamento do modelo após preparação.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o pipeline de análise de sobrevida infantil com linkage real.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--ano", type=int, default=2022, help="Ano da coorte de nascimentos a ser analisada.")
    parser.add_argument("--dir_saida", type=str, default="outputs/analise_sobrevida", help="Diretório para salvar os resultados.")
    parser.add_argument("--pop", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o arquivo CSV de população.")
    args = parser.parse_args()
    main(args)
