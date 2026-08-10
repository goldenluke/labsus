# -*- coding: utf-8 -*-
"""
======================================================================
  AUDITORIA FINANCEIRA COM ISOLATION FOREST (SIH)
======================================================================
Complementa `auditoria_ambulatorial.py` (que usa regras de negócio fixas
e Z-score simples) com um modelo de Machine Learning genuinamente
NÃO SUPERVISIONADO — Isolation Forest — para detectar internações com
padrão financeiro/temporal ANÔMALO dentro do SIH.

Ideia central do Isolation Forest: pontos anômalos são mais fáceis de
"isolar" com poucas divisões aleatórias do espaço de dados do que pontos
típicos — não exige definir manualmente limiares (diferente do Z-score),
e captura anomalias MULTIVARIADAS (ex.: um valor de internação comum,
combinado com um tempo de permanência incomum PARA AQUELE PROCEDIMENTO
específico, que isoladamente nenhuma das duas variáveis destacaria).

Cada internação é normalizada (Z-score) em relação ao seu PRÓPRIO
procedimento (PROC_REA) antes de entrar no modelo, para que a
anomalia detectada seja "incomum PARA aquele tipo de procedimento", não
apenas "caro" (procedimentos complexos são caros por natureza — isso não
é uma fraude, é esperado).
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from pysus.online_data.SIH import download as download_sih


def _achatar(x):
    """download_sih pode devolver um único arquivo ou uma lista (às vezes
    aninhada) de arquivos — achata tudo em uma sequência plana de objetos
    com .to_dataframe()."""
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_internacoes(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SIH para {uf}/{ano}...")
    downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        raise ValueError(f"Nenhum arquivo SIH encontrado para {uf}/{ano}.")
    df = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    return df


def preparar_features(df: pd.DataFrame, min_producao_procedimento: int) -> pd.DataFrame:
    colunas = ['PROC_REA', 'VAL_TOT', 'DIAS_PERM', 'IDADE', 'CNES', 'N_AIH']
    df_modelo = df[[c for c in colunas if c in df.columns]].copy()
    for col in ['VAL_TOT', 'DIAS_PERM', 'IDADE']:
        df_modelo[col] = pd.to_numeric(df_modelo[col], errors='coerce')
    df_modelo = df_modelo.dropna(subset=['VAL_TOT', 'DIAS_PERM', 'PROC_REA'])
    df_modelo = df_modelo[df_modelo['VAL_TOT'] > 0]

    contagem_proc = df_modelo['PROC_REA'].value_counts()
    procedimentos_validos = contagem_proc[contagem_proc >= min_producao_procedimento].index
    df_modelo = df_modelo[df_modelo['PROC_REA'].isin(procedimentos_validos)].copy()

    stats_proc = df_modelo.groupby('PROC_REA')[['VAL_TOT', 'DIAS_PERM']].agg(['mean', 'std'])
    stats_proc.columns = ['_'.join(c) for c in stats_proc.columns]
    df_modelo = df_modelo.merge(stats_proc, left_on='PROC_REA', right_index=True, how='left')

    df_modelo['VAL_TOT_ZSCORE'] = (df_modelo['VAL_TOT'] - df_modelo['VAL_TOT_mean']) / df_modelo['VAL_TOT_std'].replace(0, np.nan)
    df_modelo['DIAS_PERM_ZSCORE'] = (df_modelo['DIAS_PERM'] - df_modelo['DIAS_PERM_mean']) / df_modelo['DIAS_PERM_std'].replace(0, np.nan)
    df_modelo = df_modelo.dropna(subset=['VAL_TOT_ZSCORE', 'DIAS_PERM_ZSCORE'])
    return df_modelo


def detectar_anomalias(df: pd.DataFrame, contaminacao: float, seed: int) -> pd.DataFrame:
    features = df[['VAL_TOT_ZSCORE', 'DIAS_PERM_ZSCORE']].values
    modelo = IsolationForest(contamination=contaminacao, random_state=seed, n_estimators=200)
    df = df.copy()
    df['ANOMALIA'] = modelo.fit_predict(features)  # -1 = anômalo, 1 = normal
    df['SCORE_ANOMALIA'] = -modelo.score_samples(features)  # maior = mais anômalo
    return df


def gerar_grafico(df: pd.DataFrame, dir_saida: Path, uf: str):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 8))
    normal = df[df['ANOMALIA'] == 1]
    anomalo = df[df['ANOMALIA'] == -1]
    plt.scatter(normal['VAL_TOT_ZSCORE'], normal['DIAS_PERM_ZSCORE'], s=8, alpha=0.3, color='#4575b4', label='Normal')
    plt.scatter(anomalo['VAL_TOT_ZSCORE'], anomalo['DIAS_PERM_ZSCORE'], s=20, alpha=0.8, color='#d73027', label='Anômalo')
    plt.axhline(0, color='grey', linewidth=0.5)
    plt.axvline(0, color='grey', linewidth=0.5)
    plt.xlabel('Valor da AIH (desvios-padrão em relação à média DO PROCEDIMENTO)')
    plt.ylabel('Dias de Permanência (desvios-padrão em relação à média DO PROCEDIMENTO)')
    plt.title(f'Detecção de Anomalias Financeiras com Isolation Forest — {uf}')
    plt.legend()
    caminho_fig = dir_saida / f"isolation_forest_auditoria_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando internações para {args.uf}/{args.ano} ---")
    df_raw = carregar_internacoes(args.uf, args.ano)
    print(f"✅ {len(df_raw)} internações carregadas.")

    print(f"\n--- [ETAPA 2] Preparando features normalizadas por procedimento ---")
    df = preparar_features(df_raw, args.min_producao_procedimento)
    print(f"✅ {len(df)} internações com procedimento suficientemente frequente (>= {args.min_producao_procedimento} casos).")

    if len(df) < 100:
        print("❌ Poucos dados para uma detecção de anomalias confiável (mínimo recomendado: 100).")
        return

    print(f"\n--- [ETAPA 3] Detectando anomalias (Isolation Forest, contaminação={args.contaminacao}) ---")
    df = detectar_anomalias(df, args.contaminacao, args.seed)
    n_anomalias = (df['ANOMALIA'] == -1).sum()

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: AUDITORIA FINANCEIRA COM ISOLATION FOREST EM {args.uf} ---")
    print("=" * 80)
    print(f"{n_anomalias} internações ({n_anomalias / len(df):.1%}) sinalizadas como financeira/temporalmente anômalas.")
    print("\nTop 15 internações mais anômalas:")
    colunas_relatorio = ['N_AIH', 'CNES', 'PROC_REA', 'VAL_TOT', 'DIAS_PERM', 'VAL_TOT_ZSCORE', 'DIAS_PERM_ZSCORE', 'SCORE_ANOMALIA']
    colunas_relatorio = [c for c in colunas_relatorio if c in df.columns]
    print(df.sort_values('SCORE_ANOMALIA', ascending=False)[colunas_relatorio].head(15).to_string(index=False))
    print("=" * 80)

    caminho_csv = dir_saida / f"anomalias_financeiras_{args.uf.lower()}_{args.ano}.csv"
    df[df['ANOMALIA'] == -1][colunas_relatorio].sort_values('SCORE_ANOMALIA', ascending=False).to_csv(
        caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Internações anômalas salvas em: '{caminho_csv}'")

    gerar_grafico(df, dir_saida, args.uf)

    print("\n" + "=" * 80)
    print("🎉 AUDITORIA FINANCEIRA COM ISOLATION FOREST CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecta internações financeiramente anômalas com Isolation Forest.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--min-producao-procedimento", type=int, default=30, help="Produção mínima de um procedimento para ser incluído na análise (garante uma média/desvio-padrão confiáveis).")
    parser.add_argument("--contaminacao", type=float, default=0.02, help="Proporção esperada de anomalias na base (parâmetro do Isolation Forest).")
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatória.")
    parser.add_argument("--dir_saida", type=str, default="outputs/isolation_forest_auditoria", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
