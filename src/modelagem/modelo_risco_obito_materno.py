# -*- coding: utf-8 -*-
"""
======================================================================
  TRIAGEM DE ÓBITOS MATERNOS POSSIVELMENTE MAL CLASSIFICADOS (SIM)
======================================================================
A mortalidade materna é um dos indicadores mais monitorados em saúde
pública (meta dos ODS), mas sofre de SUBNOTIFICAÇÃO/MÁ CLASSIFICAÇÃO
crônica no Brasil: óbitos de mulheres grávidas ou puérperas às vezes têm
a causa básica registrada incorretamente, exigindo que Comitês de
Mortalidade Materna investiguem manualmente TODOS os óbitos de mulheres
em idade fértil (10-49 anos) para encontrar óbitos maternos "escondidos"
sob causas mal definidas ou aparentemente não-obstétricas.

Este script treina um classificador (LightGBM + SHAP) para distinguir,
entre óbitos de mulheres em idade fértil, quais características
sociodemográficas e assistenciais mais se associam a uma causa básica
JÁ CLASSIFICADA como obstétrica (CID-10 Capítulo XV, O00-O99) — servindo
como um SCORE DE PRIORIZAÇÃO para direcionar o esforço manual dos
Comitês de Mortalidade Materna aos óbitos mais suspeitos de serem
maternos mesmo quando codificados com uma causa não-obstétrica (alto
score do modelo + causa não-O = forte candidato à investigação).
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt

from pysus.online_data.SIM import download as download_sim

IDADE_MIN_FERTIL = 10
IDADE_MAX_FERTIL = 49


def carregar_obitos_mulheres_idade_fertil(uf: str, anos: list) -> pd.DataFrame:
    dfs = []
    for ano in anos:
        print(f"[LOG] Baixando SIM para {uf}/{ano}...")
        try:
            downloaded = download_sim(states=uf, years=ano, groups=['CID10'])
        except Exception as e:
            print(f"  -> ❌ Falha ao baixar {ano}: {e}")
            continue
        if isinstance(downloaded, list):
            if not downloaded:
                print(f"  -> Nenhum dado disponível para {ano} (ainda não publicado).")
                continue
            df_ano = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True)
        else:
            df_ano = downloaded.to_dataframe()
        dfs.append(df_ano)
    if not dfs:
        raise ValueError("Nenhum dado do SIM pôde ser carregado.")
    df = pd.concat(dfs, ignore_index=True)

    df = df[df['SEXO'].astype(str) == '2'].copy()  # 2 = Feminino
    idade_num = pd.to_numeric(df['IDADE'], errors='coerce')
    idade_anos = idade_num.where(idade_num < 500) - 400  # código DATASUS: 4XX = XX anos completos
    df = df[(idade_anos >= IDADE_MIN_FERTIL) & (idade_anos <= IDADE_MAX_FERTIL)].copy()
    df['IDADE_ANOS'] = idade_anos.loc[df.index]
    return df


def preparar_dados(df: pd.DataFrame):
    df = df.copy()
    df['CAUSABAS'] = df['CAUSABAS'].astype(str)
    df['ALVO_OBSTETRICO'] = df['CAUSABAS'].str.upper().str.startswith('O').astype(int)

    colunas_candidatas = ['IDADE_ANOS', 'RACACOR', 'ESC', 'ESTCIV', 'LOCOCOR', 'ASSISTMED', 'CIRCOBITO', 'URBRUR']
    colunas_existentes = [c for c in colunas_candidatas if c in df.columns]
    print(f"[LOG] Features disponíveis para o modelo: {colunas_existentes}")

    df_modelo = df[colunas_existentes + ['ALVO_OBSTETRICO']].copy()
    for col in colunas_existentes:
        if col != 'IDADE_ANOS':
            df_modelo[col] = df_modelo[col].astype(str).astype('category')
    df_modelo['IDADE_ANOS'] = pd.to_numeric(df_modelo['IDADE_ANOS'], errors='coerce')
    df_modelo = df_modelo.dropna(subset=['IDADE_ANOS'])

    y = df_modelo['ALVO_OBSTETRICO']
    X = df_modelo.drop(columns=['ALVO_OBSTETRICO'])
    return X, y


def treinar_modelo(X: pd.DataFrame, y: pd.Series, dir_saida: Path):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    ratio = y_train.value_counts().get(0, 1) / max(y_train.value_counts().get(1, 1), 1)
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)
    modelo.fit(X_train, y_train)

    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    y_pred = modelo.predict(X_test)
    print("\n--- Relatório de Classificação (conjunto de teste) ---")
    print(classification_report(y_test, y_pred, zero_division=0, target_names=['Não-obstétrico', 'Obstétrico (materno)']))
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"AUC (Área sob a Curva ROC): {auc:.4f}")

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)
    shap_values_risco = shap_values[1] if isinstance(shap_values, list) else shap_values

    plt.figure()
    shap.summary_plot(shap_values_risco, X_test, plot_type="bar", show=False)
    plt.title("Fatores Associados a Óbito Classificado como Obstétrico (SHAP)")
    plt.tight_layout()
    caminho_fig = dir_saida / "shap_risco_obito_materno.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico SHAP salvo em: {caminho_fig}")

    return modelo, auc


def priorizar_casos_suspeitos(modelo, X: pd.DataFrame, df_original: pd.DataFrame, limiar: float, dir_saida: Path):
    """Aplica o modelo a TODOS os óbitos não classificados como obstétricos e
    lista os que têm maior probabilidade prevista — candidatos a óbito materno
    'escondido' que merece investigação do Comitê de Mortalidade Materna."""
    df_nao_obstetrico = df_original.loc[X.index][df_original.loc[X.index, 'CAUSABAS'].astype(str).str.upper().str.startswith('O') == False]
    if df_nao_obstetrico.empty:
        return pd.DataFrame()
    X_suspeitos = X.loc[df_nao_obstetrico.index]
    scores = modelo.predict_proba(X_suspeitos)[:, 1]
    df_nao_obstetrico = df_nao_obstetrico.copy()
    df_nao_obstetrico['SCORE_SUSPEITA_OBITO_MATERNO'] = scores
    suspeitos = df_nao_obstetrico[df_nao_obstetrico['SCORE_SUSPEITA_OBITO_MATERNO'] >= limiar]
    return suspeitos.sort_values('SCORE_SUSPEITA_OBITO_MATERNO', ascending=False)


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando óbitos de mulheres em idade fértil (10-49 anos) para {args.uf}/{args.anos} ---")
    df_raw = carregar_obitos_mulheres_idade_fertil(args.uf, args.anos)
    print(f"✅ {len(df_raw)} óbitos carregados.")

    print(f"\n--- [ETAPA 2] Preparando dados (alvo: causa obstétrica CID-10 O00-O99) ---")
    X, y = preparar_dados(df_raw)
    print(f"✅ {len(X)} casos válidos. Proporção classificada como obstétrica: {y.mean():.1%}")

    if len(X) < 100 or y.nunique() < 2:
        print("❌ Dados insuficientes para treinar o modelo (mínimo recomendado: 100 óbitos, com ambas as classes).")
        return

    print(f"\n--- [ETAPA 3] Treinando classificador ---")
    modelo, auc = treinar_modelo(X, y, dir_saida)

    print(f"\n--- [ETAPA 4] Priorizando óbitos NÃO-obstétricos suspeitos de serem maternos mal classificados ---")
    suspeitos = priorizar_casos_suspeitos(modelo, X, df_raw, args.limiar_suspeita, dir_saida)
    print(f"✅ {len(suspeitos)} óbitos não-obstétricos sinalizados com score >= {args.limiar_suspeita} para investigação prioritária.")

    if not suspeitos.empty:
        from src.utils.dataloaders import adicionar_nome_municipio
        suspeitos = adicionar_nome_municipio(suspeitos, 'CODMUNRES', args.populacao)
        colunas_relatorio = [c for c in ['CODMUNRES', 'municipio', 'DTOBITO', 'IDADE_ANOS', 'CAUSABAS', 'SCORE_SUSPEITA_OBITO_MATERNO'] if c in suspeitos.columns]
        caminho_csv = dir_saida / f"obitos_suspeitos_maternos_{args.uf.lower()}.csv"
        suspeitos[colunas_relatorio].to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"📄 Lista de priorização salva em: '{caminho_csv}'")
        print(suspeitos[colunas_relatorio].head(15).to_string(index=False))

    print("\n" + "=" * 80)
    print("🎉 TRIAGEM DE ÓBITOS MATERNOS CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo para priorizar óbitos de mulheres em idade fértil suspeitos de serem maternos mal classificados.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SIM a usar.")
    parser.add_argument("--limiar-suspeita", type=float, default=0.5, help="Score mínimo (probabilidade prevista) para sinalizar um óbito não-obstétrico como suspeito.")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada (usado para mapear nomes de município).")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_obito_materno", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
