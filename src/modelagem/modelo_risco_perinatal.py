# -*- coding: utf-8 -*-
"""
======================================================================
  MODELO PREDITIVO DE RISCO PERINATAL (BAIXO PESO E PREMATURIDADE)
======================================================================
Este script treina um modelo de Machine Learning para prever a
probabilidade de um recém-nascido apresentar um desfecho de risco
(baixo peso ao nascer < 2500g OU prematuridade < 37 semanas).

Fonte de Dados: Sistema de Informações sobre Nascidos Vivos (SINASC).
"""

import pandas as pd
from pathlib import Path
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import shap
import os

from pysus.online_data.SINASC import download as download_sinasc

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import lightgbm as lgb

def carregar_dados_sinasc(ufs: list, anos: list) -> pd.DataFrame:
    """
    Baixa e consolida dados do SINASC usando a lógica de download funcional.
    """
    print(f"\n--- [ETAPA 1] Carregando dados do SINASC para UFs: {ufs}, Anos: {anos} ---")
    all_dfs = []
    for uf in ufs:
        for ano in anos:
            try:
                print(f"[LOG] Tentando baixar dados para {uf}/{ano}...")
                sinasc_data = download_sinasc(states=uf, years=ano, groups=["DN"])
                if not sinasc_data: raise ValueError("Nenhum arquivo SINASC encontrado.")

                if isinstance(sinasc_data, list):
                    df_ano_uf = pd.concat([f.to_dataframe() for f in sinasc_data], ignore_index=True)
                elif hasattr(sinasc_data, "to_dataframe"):
                    df_ano_uf = sinasc_data.to_dataframe()
                else:
                    raise TypeError("O objeto baixado do SINASC não pôde ser convertido para DataFrame.")

                if df_ano_uf.empty: raise ValueError("DataFrame do SINASC está vazio.")
                all_dfs.append(df_ano_uf)
                print(f"  -> Sucesso! {len(df_ano_uf)} registros carregados para {uf}/{ano}.")

            except Exception as e:
                print(f"  -> ❌ Falha ao baixar ou processar dados para {uf}/{ano}. Erro: {e}")

    if not all_dfs:
        print("❌ Erro crítico: Nenhum dado do SINASC pôde ser carregado.")
        return pd.DataFrame()

    df_completo = pd.concat(all_dfs, ignore_index=True)
    print(f"\n✅ Dados do SINASC carregados com sucesso. Total de {len(df_completo)} registros.")
    return df_completo

def preparar_dados(df: pd.DataFrame):
    """Limpa os dados, cria a variável alvo e prepara as features para o modelo."""
    print("\n--- [ETAPA 2] Pré-processamento e Engenharia de Features ---")
    features_iniciais = [
        'PESO', 'GESTACAO', 'IDADEMAE', 'ESCMAE2010', 'RACACORMAE',
        'QTDFILVIVO', 'QTDFILMORT', 'CONSPRENAT', 'MESPRENAT',
        'PARTO', 'GRAVIDEZ', 'ESTCIVMAE'
    ]
    features_presentes = [col for col in features_iniciais if col in df.columns]
    print(f"[LOG] Colunas encontradas e selecionadas: {features_presentes}")

    df_selecionado = df[features_presentes].copy()

    # Converte colunas para numérico
    for col in features_presentes:
        df_selecionado[col] = pd.to_numeric(df_selecionado[col], errors='coerce')

    # Remove linhas com valores nulos
    initial_rows = len(df_selecionado)
    df_limpo = df_selecionado.dropna()
    print(f"[LOG] {initial_rows - len(df_limpo)} registros removidos por conterem valores ausentes.")

    if len(df_limpo) < 1000:
        print("❌ Aviso: A quantidade de dados válidos é muito baixa para treinar um modelo confiável.")
        return pd.DataFrame(), pd.Series()

    # Criação da variável alvo
    df_limpo['BAIXO_PESO'] = (df_limpo['PESO'] < 2500).astype(int)
    # GESTACAO: 5 = 37 a 41 semanas (a termo). Valores menores são prematuros.
    df_limpo['PREMATURO'] = (df_limpo['GESTACAO'] < 5).astype(int)
    df_limpo['ALVO_RISCO'] = ((df_limpo['BAIXO_PESO'] == 1) | (df_limpo['PREMATURO'] == 1)).astype(int)

    y = df_limpo['ALVO_RISCO']
    X = df_limpo.drop(columns=['PESO', 'GESTACAO', 'BAIXO_PESO', 'PREMATURO', 'ALVO_RISCO'])

    print(f"✅ Dados preparados. Features (X) shape: {X.shape}, Alvo (y) shape: {y.shape}")
    print("\nDistribuição da variável alvo:")
    print(y.value_counts(normalize=True))

    return X, y

def treinar_e_avaliar_modelo(X: pd.DataFrame, y: pd.Series, dir_saida: Path):
    """Treina, avalia, interpreta com SHAP e salva o modelo de classificação."""
    print("\n--- [ETAPA 3, 4 & 5] Treinamento, Avaliação e Interpretação ---")
    dir_saida.mkdir(parents=True, exist_ok=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    # Trata o desbalanceamento de classes
    try:
        ratio = y_train.value_counts()[0] / y_train.value_counts()[1]
    except ZeroDivisionError:
        print("❌ Erro: A variável alvo não tem variação no conjunto de treino. Impossível treinar o modelo.")
        return

    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio, n_jobs=-1)

    print("[LOG] Treinando o modelo LightGBM...")
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")

    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]

    print("\n--- Performance do Modelo no Conjunto de Teste ---")
    print("\nRelatório de Classificação:")
    print(classification_report(y_test, y_pred, zero_division=0))
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"Área sob a Curva ROC (AUC): {auc:.4f}")

    print("\n[LOG] Calculando os valores SHAP...")
    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)

    mapa_rotulos = {
        'IDADEMAE': 'Idade da Mãe', 'ESCMAE2010': 'Escolaridade da Mãe', 'RACACORMAE': 'Raça/Cor da Mãe',
        'QTDFILVIVO': 'Nº de Filhos Vivos', 'QTDFILMORT': 'Nº de Filhos Mortos', 'CONSPRENAT': 'Nº Consultas Pré-Natal',
        'MESPRENAT': 'Mês Início Pré-Natal', 'PARTO': 'Tipo de Parto', 'GRAVIDEZ': 'Tipo de Gravidez',
        'ESTCIVMAE': 'Estado Civil da Mãe'
    }
    X_test_renomeado = X_test.rename(columns=mapa_rotulos)

    # --- CORREÇÃO FINAL APLICADA AQUI ---
    # `shap_values` é uma lista com 2 arrays. Para os gráficos, precisamos
    # do array correspondente à classe positiva (classe 1).
    if isinstance(shap_values, list):
        shap_values_risk = shap_values[1]
    else:
        shap_values_risk = shap_values
    # --- FIM DA CORREÇÃO ---

    # 1. Gráfico de Resumo SHAP (Barras)
    plt.figure()
    # Passamos a matriz de valores da classe 1 diretamente para a função.
    shap.summary_plot(shap_values_risk, features=X_test_renomeado, plot_type="bar", show=False)
    plt.title("Impacto Médio de Cada Fator no Risco (SHAP)", fontsize=16)
    plt.tight_layout()
    caminho_shap_bar = dir_saida / "shap_summary_bar.png"
    plt.savefig(caminho_shap_bar, dpi=150)
    plt.close()
    print(f"📈 Gráfico SHAP de barras salvo em: {caminho_shap_bar}")

    # 2. Gráfico de Resumo SHAP (Nuvem de Pontos)
    plt.figure()
    # Passamos a matriz de valores da classe 1 diretamente para a função.
    shap.summary_plot(shap_values_risk, features=X_test_renomeado, show=False)
    plt.title("Distribuição do Impacto de Cada Fator (SHAP)", fontsize=16)
    plt.tight_layout()
    caminho_shap_beeswarm = dir_saida / "shap_summary_beeswarm.png"
    plt.savefig(caminho_shap_beeswarm, dpi=150)
    plt.close()
    print(f"📈 Gráfico SHAP de nuvem de pontos salvo em: {caminho_shap_beeswarm}")

    caminho_modelo = dir_saida / "modelo_risco_perinatal.joblib"
    joblib.dump(modelo, caminho_modelo)
    print(f"\n💾 Modelo de previsão salvo em: {caminho_modelo}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo para prever risco perinatal (baixo peso/prematuridade).")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar. Ex: TO SP RJ")
    parser.add_argument("--anos", nargs="+", type=int, default=[2023], help="Anos de dados históricos a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_perinatal", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    df_raw = carregar_dados_sinasc(ufs=args.ufs, anos=args.anos)

    if not df_raw.empty:
        X, y = preparar_dados(df_raw)
        if not X.empty:
            treinar_e_avaliar_modelo(X, y, Path(args.dir_saida))
            print("\n" + "="*80)
            print("🎉 PIPELINE DE MODELAGEM CONCLUÍDO COM SUCESSO! 🎉")
            print("="*80)
