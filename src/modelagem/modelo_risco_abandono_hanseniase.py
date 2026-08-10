# -*- coding: utf-8 -*-
"""
======================================================================
  MODELO PREDITIVO DE RISCO DE ABANDONO DO TRATAMENTO DE HANSENÍASE
======================================================================
A hanseníase é uma doença tropical negligenciada de alta prioridade no
Brasil (um dos poucos países que ainda não eliminou a doença como
problema de saúde pública), com tratamento longo (6 a 12 meses de
Poliquimioterapia) — abandono do tratamento favorece recidiva,
transmissão continuada e sequelas neurológicas permanentes (incapacidade
física). Este script espelha `modelo_risco_abandono_tb.py` para o SINAN
de Hanseníase (dis_code=HANS), usando os campos oficiais documentados no
Apêndice do dicionário de dados do projeto: classificação operacional
(CLASSOPERA: Pauci/Multibacilar), forma clínica (FORMACLINI), grau de
incapacidade física ao diagnóstico (AVALIA_N — um forte preditor clínico
conhecido de má adesão), número de lesões e nervos afetados, e perfil
sociodemográfico — para prever, no momento do diagnóstico, a
probabilidade de abandono (TPALTA_N = 7) em vez de cura.
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt

from pysus.online_data.SINAN import SINAN


def carregar_dados_hanseniase(anos: list) -> pd.DataFrame:
    sinan_db = SINAN().load()
    files = sinan_db.get_files(dis_code='HANS', year=anos)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo SINAN/HANS encontrado para {anos}.")
    downloaded = sinan_db.download(files)
    df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    return df


def preparar_dados(df: pd.DataFrame):
    if 'TPALTA_N' not in df.columns:
        raise KeyError("Coluna 'TPALTA_N' (tipo de alta/encerramento) não encontrada nos dados do SINAN/HANS.")

    df['TPALTA_N'] = pd.to_numeric(df['TPALTA_N'], errors='coerce')
    df_analise = df[df['TPALTA_N'].isin([1, 7])].copy()  # 1=Cura, 7=Abandono (foco do modelo)
    df_analise['ALVO_ABANDONO'] = (df_analise['TPALTA_N'] == 7).astype(int)
    print("[LOG] Foco da análise: casos com desfecho de Cura ou Abandono.")
    print(f"Distribuição do alvo 'ALVO_ABANDONO':\n{df_analise['ALVO_ABANDONO'].value_counts(normalize=True)}")

    features_numericas = ['NU_LESOES', 'AVALIA_N', 'NERVOSAFET', 'CONTREG']
    features_categoricas = ['CS_SEXO', 'CS_RACA', 'CS_ESCOL_N', 'FORMACLINI', 'CLASSOPERA', 'MODOENTR', 'MODODETECT', 'BACILOSCOP', 'ESQ_INI_N']

    features_num_existentes = [c for c in features_numericas if c in df_analise.columns]
    features_cat_existentes = [c for c in features_categoricas if c in df_analise.columns]
    print(f"[LOG] Features numéricas: {features_num_existentes}")
    print(f"[LOG] Features categóricas: {features_cat_existentes}")

    y = df_analise['ALVO_ABANDONO']
    X = df_analise[features_num_existentes + features_cat_existentes].copy()

    if 'NU_IDADE_N' in df_analise.columns:
        idade_str = df_analise['NU_IDADE_N'].astype(str)
        idade_valida = (idade_str.str.len() == 4) & (idade_str.str.startswith('4'))
        idade = pd.to_numeric(idade_str.str[1:], errors='coerce')
        X['IDADE'] = idade.where(idade_valida)

    for col in features_num_existentes + (['IDADE'] if 'IDADE' in X.columns else []):
        X[col] = pd.to_numeric(X[col], errors='coerce')
    for col in features_cat_existentes:
        X[col] = X[col].astype(str)

    X = X.dropna(subset=[c for c in features_num_existentes + (['IDADE'] if 'IDADE' in X.columns else [])])
    y = y.loc[X.index]

    X = pd.get_dummies(X, columns=features_cat_existentes, drop_first=True)
    X = X.fillna(-1)
    return X, y


def treinar_e_interpretar(X: pd.DataFrame, y: pd.Series, dir_saida: Path):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    if y_train.nunique() < 2:
        print("❌ Erro: o conjunto de treino contém apenas uma classe.")
        return None, None

    ratio = y_train.value_counts()[0] / y_train.value_counts()[1] if y_train.value_counts().get(1, 0) > 0 else 1
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)
    modelo.fit(X_train, y_train)

    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n--- Performance do Modelo (conjunto de teste) ---\nAUC: {auc:.4f}")

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)
    shap_values_risco = shap_values[1] if isinstance(shap_values, list) else shap_values

    plt.figure()
    shap.summary_plot(shap_values_risco, X_test, plot_type="bar", show=False)
    plt.title("Fatores de Risco para Abandono do Tratamento de Hanseníase (SHAP)")
    plt.tight_layout()
    caminho_fig = dir_saida / "shap_abandono_hanseniase.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico SHAP salvo em: {caminho_fig}")

    return modelo, auc


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando dados de Hanseníase (SINAN/HANS) para {args.anos} ---")
    df_raw = carregar_dados_hanseniase(args.anos)
    print(f"✅ {len(df_raw)} notificações carregadas.")

    print(f"\n--- [ETAPA 2] Preparando dados ---")
    X, y = preparar_dados(df_raw)
    print(f"✅ {len(X)} casos válidos.")

    if len(X) < 50 or y.nunique() < 2:
        print("❌ Dados insuficientes para treinar o modelo (mínimo recomendado: 50 casos, com ambas as classes).")
        return

    print(f"\n--- [ETAPA 3] Treinando e interpretando o modelo ---")
    treinar_e_interpretar(X, y, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 MODELO DE RISCO DE ABANDONO DE HANSENÍASE CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo para prever o risco de abandono do tratamento de Hanseníase.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022, 2023], help="Anos de dados históricos do SINAN-HANS a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_abandono_hanseniase", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
