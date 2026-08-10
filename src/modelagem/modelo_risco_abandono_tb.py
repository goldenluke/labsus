# -*- coding: utf-8 -*-
"""
======================================================================
  MODELO PREDITIVO DE RISCO DE ABANDONO DO TRATAMENTO DA TUBERCULOSE
======================================================================
Este script treina um modelo de Machine Learning para prever, no momento
do diagnóstico, a probabilidade de um paciente com tuberculose abandonar
o tratamento.
"""

import pandas as pd
from pathlib import Path
import argparse

# Importações do PySUS
from pysus.online_data.SINAN import SINAN

# Ferramentas de Machine Learning
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt


def carregar_dados_tuberculose(anos: list):
    """Carrega múltiplos anos de dados do SINAN para Tuberculose."""
    print(f"\n--- [ETAPA 1] Carregando dados de Tuberculose (TUBE) para os anos: {anos} ---")

    try:
        sinan_db = SINAN().load()
        files = sinan_db.get_files(dis_code='TUBE', year=anos)
        if not files:
            print("⚠️ Nenhum arquivo SINAN/TUBE encontrado para os anos fornecidos.")
            return pd.DataFrame()

        print(f"[LOG] Baixando e processando {len(files)} arquivo(s)...")
        downloaded = sinan_db.download(files)

        if isinstance(downloaded, list):
            df = pd.concat([p.to_dataframe() for p in downloaded if hasattr(p, 'to_dataframe')], ignore_index=True)
        elif hasattr(downloaded, "to_dataframe"):
            df = downloaded.to_dataframe()
        else:
            df = pd.DataFrame()

        print(f"✅ Dados de Tuberculose carregados com sucesso. Total de {len(df)} notificações.")
        return df

    except Exception as e:
        print(f"❌ Erro crítico durante o carregamento de dados: {e}")
        return pd.DataFrame()


def preparar_dados(df: pd.DataFrame):
    """Limpa os dados, cria a variável alvo e prepara as features para o modelo."""
    print("\n--- [ETAPA 2] Pré-processamento e Engenharia de Features ---")

    features_iniciais = [
        'SITUA_ENCE', 'NU_IDADE_N', 'CS_SEXO', 'CS_RACA', 'CS_ESCOL_N',
        'AGRA_ALCOO', 'AGRA_DIABE', 'AGRA_DOENC', 'AGRA_HIV', 'AGRA_TABAC',
        'FORMA', 'BACILOSC_E', 'RAIOX_TORA', 'TRAT_SUPER'
    ]
    df_modelo = df[[col for col in features_iniciais if col in df.columns]].copy()

    df_modelo['SITUA_ENCE'] = pd.to_numeric(df_modelo['SITUA_ENCE'], errors='coerce')
    df_analise = df_modelo[df_modelo['SITUA_ENCE'].isin([1, 2])].copy()

    df_analise['ALVO_ABANDONO'] = (df_analise['SITUA_ENCE'] == 2).astype(int)

    print("[LOG] Foco da análise: Casos com desfecho de Cura ou Abandono.")
    print(f"Distribuição da variável alvo:\n{df_analise['ALVO_ABANDONO'].value_counts(normalize=True)}")

    y = df_analise['ALVO_ABANDONO']
    X = df_analise.drop(columns=['SITUA_ENCE', 'ALVO_ABANDONO'])

    if 'NU_IDADE_N' in X.columns:
        X['NU_IDADE_N'] = X['NU_IDADE_N'].astype(str)
        valid_age_mask = (X['NU_IDADE_N'].str.len() == 4) & (X['NU_IDADE_N'].str.startswith('4'))
        X['IDADE'] = X['NU_IDADE_N'].str[1:]
        X['IDADE'] = pd.to_numeric(X['IDADE'], errors='coerce')
        X = X[valid_age_mask & X['IDADE'].notna()].copy()
        y = y.loc[X.index]
        X = X.drop(columns=['NU_IDADE_N'])

    potential_categorical_cols = [
        'CS_SEXO', 'CS_RACA', 'CS_ESCOL_N', 'AGRA_ALCOO', 'AGRA_DIABE',
        'AGRA_DOENC', 'AGRA_HIV', 'AGRA_TABAC', 'FORMA',
        'BACILOSC_E', 'RAIOX_TORA', 'TRAT_SUPER'
    ]

    categorical_cols_existentes = [col for col in potential_categorical_cols if col in X.columns]
    print(f"[LOG] Colunas categóricas encontradas para o modelo: {categorical_cols_existentes}")

    for col in categorical_cols_existentes:
        X[col] = X[col].astype(str)

    X = pd.get_dummies(X, columns=categorical_cols_existentes, drop_first=True)

    X = X.fillna(-1)

    print(f"✅ Dados preparados. Features (X) shape: {X.shape}, Alvo (y) shape: {y.shape}")
    return X, y


def treinar_e_interpretar_modelo(X: pd.DataFrame, y: pd.Series, dir_saida: Path):
    """Treina, avalia e interpreta o modelo de classificação."""
    print("\n--- [ETAPA 3] Treinamento e Interpretação do Modelo de Risco de Abandono ---")
    dir_saida.mkdir(parents=True, exist_ok=True)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    if y_train.nunique() < 2:
        print("❌ Erro: O conjunto de treino contém apenas uma classe."); return

    ratio = y_train.value_counts()[0] / y_train.value_counts()[1] if y_train.value_counts().get(1, 0) > 0 else 1
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)

    print("[LOG] Treinando o modelo LightGBM...")
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")

    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n--- Performance do Modelo no Conjunto de Teste ---")
    print(f"Área sob a Curva ROC (AUC): {auc:.4f}")

    print("\n[LOG] Calculando os valores SHAP...")
    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)

    mapa_rotulos = {
        'CS_SEXO': 'Sexo', 'CS_RACA': 'Raça/Cor', 'CS_ESCOL_N': 'Escolaridade',
        'AGRA_ALCOO': 'Alcoolismo Associado', 'AGRA_DIABE': 'Diabetes Associada',
        'AGRA_DOENC': 'Doença Mental Associada', 'AGRA_HIV': 'HIV/AIDS Associado',
        'AGRA_TABAC': 'Tabagismo Associado', 'FORMA': 'Forma Clínica da TB',
        'BACILOSC_E': 'Resultado Baciloscopia', 'RAIOX_TORA': 'Resultado Raio-X',
        'TRAT_SUPER': 'Tratamento Supervisionado (TDO)', 'IDADE': 'Idade'
    }

    def renomear_colunas_dummy(col_name):
        for original, amigavel in mapa_rotulos.items():
            if col_name.startswith(original + '_'):
                return col_name.replace(original, amigavel)
        return mapa_rotulos.get(col_name, col_name)

    X_test_renomeado = X_test.rename(columns=renomear_colunas_dummy)

    # ==========================================================
    # --- CORREÇÃO APLICADA AQUI ---
    # Extrai a matriz de valores da classe 1 (risco) explicitamente
    # e passa os componentes (valores, dados, nomes das colunas) separadamente.
    # ==========================================================
    shap_values_risk = shap_values

    plt.figure()
    shap.summary_plot(
        shap_values_risk,
        features=X_test.values,
        feature_names=X_test_renomeado.columns.tolist(),
        plot_type="bar",
        show=False
    )
    plt.title("Principais Fatores de Risco para Abandono do Tratamento de TB")
    plt.tight_layout()
    caminho_fig = dir_saida / "feature_importance_abandono_tb.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight'); plt.close()
    print(f"📈 Gráfico SHAP de importância salvo em: {caminho_fig}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo para prever o risco de abandono do tratamento de Tuberculose.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022, 2023], help="Anos de dados históricos do SINAN-TB a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_abandono_tb", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    # Pipeline
    df_raw = carregar_dados_tuberculose(anos=args.anos)

    if df_raw is not None and not df_raw.empty:
        X, y = preparar_dados(df_raw)
        if not X.empty and y.nunique() > 1:
            treinar_e_interpretar_modelo(X, y, Path(args.dir_saida))
            print("\n" + "="*80)
            print("🎉 PIPELINE DE RISCO DE ABANDONO CONCLUÍDO! 🎉")
            print("="*80)
