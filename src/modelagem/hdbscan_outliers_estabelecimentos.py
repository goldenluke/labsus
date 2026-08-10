# -*- coding: utf-8 -*-
"""
======================================================================
  ESTABELECIMENTOS ATÍPICOS COM HDBSCAN (SIA)
======================================================================
Este script constrói um perfil de produção ambulatorial por
estabelecimento (volume total, diversidade de procedimentos, valor médio,
proporção de procedimentos de alta complexidade) e aplica HDBSCAN
(clustering hierárquico baseado em densidade) para agrupar estabelecimentos
com perfil semelhante.

Diferente do K-Means usado em `clusters.py` (que força TODO estabelecimento
a pertencer a algum cluster, mesmo que ele não se pareça com nenhum outro,
e exige definir k manualmente), o HDBSCAN:
  1) Descobre sozinho o número de grupos naturais nos dados;
  2) Marca explicitamente como "RUÍDO" (outlier) qualquer estabelecimento
     que não se encaixe bem em nenhum grupo denso — exatamente os
     estabelecimentos mais "atípicos" da rede, que merecem atenção
     (podem ser unidades altamente especializadas, mal cadastradas, ou
     com padrão de produção fora do esperado para o seu porte/tipo).
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import hdbscan
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from pysus.online_data.SIA import download as download_sia


def _achatar(x):
    """download_sia pode devolver um único arquivo, uma lista, ou uma lista
    de listas (um nível por grupo/mês) — achata tudo em uma sequência plana
    de objetos com .to_dataframe()."""
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_producao(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SIA/PA para {uf}/{ano}...")
    downloaded = download_sia(states=uf, years=ano, months=list(range(1, 13)), groups=['PA'])
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        raise ValueError(f"Nenhum arquivo SIA/PA encontrado para {uf}/{ano}.")
    df = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    return df


def construir_perfil_estabelecimentos(df: pd.DataFrame, producao_minima: int) -> pd.DataFrame:
    colunas = ['PA_CODUNI', 'PA_PROC_ID', 'PA_VALAPR', 'PA_QTDAPR', 'PA_CIDPRI']
    df = df[[c for c in colunas if c in df.columns]].copy()
    df['PA_VALAPR'] = pd.to_numeric(df['PA_VALAPR'], errors='coerce')
    df['PA_QTDAPR'] = pd.to_numeric(df['PA_QTDAPR'], errors='coerce')
    df = df.dropna(subset=['PA_CODUNI', 'PA_VALAPR', 'PA_QTDAPR'])

    grupo = df.groupby('PA_CODUNI')
    perfil = pd.DataFrame({
        'VOLUME_TOTAL': grupo['PA_QTDAPR'].sum(),
        'VALOR_TOTAL': grupo['PA_VALAPR'].sum(),
        'VALOR_MEDIO_POR_PROCEDIMENTO': grupo['PA_VALAPR'].mean(),
        'N_PROCEDIMENTOS_DISTINTOS': grupo['PA_PROC_ID'].nunique(),
        'N_DIAGNOSTICOS_DISTINTOS': grupo['PA_CIDPRI'].nunique() if 'PA_CIDPRI' in df.columns else 0,
    })
    perfil['DIVERSIDADE_PROCEDIMENTOS'] = perfil['N_PROCEDIMENTOS_DISTINTOS'] / perfil['VOLUME_TOTAL']
    perfil = perfil[perfil['VOLUME_TOTAL'] >= producao_minima].reset_index()
    return perfil


def detectar_clusters_e_outliers(perfil: pd.DataFrame, min_cluster_size: int):
    colunas_features = ['VOLUME_TOTAL', 'VALOR_MEDIO_POR_PROCEDIMENTO', 'N_PROCEDIMENTOS_DISTINTOS', 'DIVERSIDADE_PROCEDIMENTOS']
    X = perfil[colunas_features].copy()
    X_log = np.log1p(X[['VOLUME_TOTAL', 'VALOR_MEDIO_POR_PROCEDIMENTO', 'N_PROCEDIMENTOS_DISTINTOS']])
    X_final = pd.concat([X_log, X[['DIVERSIDADE_PROCEDIMENTOS']]], axis=1)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_final)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, prediction_data=False)
    labels = clusterer.fit_predict(X_scaled)

    perfil = perfil.copy()
    perfil['CLUSTER'] = labels
    perfil['E_OUTLIER'] = labels == -1
    perfil['SCORE_OUTLIER'] = clusterer.outlier_scores_

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)
    perfil['PCA_1'], perfil['PCA_2'] = coords[:, 0], coords[:, 1]

    return perfil


def gerar_grafico(perfil: pd.DataFrame, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    plt.figure(figsize=(11, 9))
    normais = perfil[~perfil['E_OUTLIER']]
    outliers = perfil[perfil['E_OUTLIER']]
    scatter = plt.scatter(normais['PCA_1'], normais['PCA_2'], c=normais['CLUSTER'], cmap=cm.tab10, alpha=0.6, s=30, label='Clusters')
    plt.scatter(outliers['PCA_1'], outliers['PCA_2'], color='black', marker='x', s=60, label=f'Outliers (n={len(outliers)})')
    plt.legend()
    plt.title(f"Perfis de Produção Ambulatorial — Clusters (HDBSCAN) e Outliers — {uf}")
    plt.xlabel('Componente Principal 1')
    plt.ylabel('Componente Principal 2')
    caminho_fig = dir_saida / f"hdbscan_estabelecimentos_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando produção ambulatorial para {args.uf}/{args.ano} ---")
    df_raw = carregar_producao(args.uf, args.ano)
    print(f"✅ {len(df_raw)} registros de produção carregados.")

    print(f"\n--- [ETAPA 2] Construindo perfil de produção por estabelecimento ---")
    perfil = construir_perfil_estabelecimentos(df_raw, args.producao_minima)
    print(f"✅ {len(perfil)} estabelecimentos com produção >= {args.producao_minima}.")

    if len(perfil) < 20:
        print("❌ Poucos estabelecimentos para uma análise de clustering confiável (mínimo recomendado: 20).")
        return

    print(f"\n--- [ETAPA 3] Detectando clusters e outliers (HDBSCAN, min_cluster_size={args.min_cluster_size}) ---")
    perfil = detectar_clusters_e_outliers(perfil, args.min_cluster_size)
    n_clusters = perfil[perfil['CLUSTER'] != -1]['CLUSTER'].nunique()
    n_outliers = perfil['E_OUTLIER'].sum()

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: PERFIS DE ESTABELECIMENTOS EM {args.uf} ---")
    print("=" * 80)
    print(f"{n_clusters} clusters naturais de estabelecimentos detectados.")
    print(f"{n_outliers} estabelecimentos ({n_outliers / len(perfil):.1%}) identificados como atípicos (outliers/ruído).")
    print("\nTop 15 estabelecimentos mais atípicos:")
    print(perfil[perfil['E_OUTLIER']].sort_values('SCORE_OUTLIER', ascending=False)
          [['PA_CODUNI', 'VOLUME_TOTAL', 'VALOR_MEDIO_POR_PROCEDIMENTO', 'N_PROCEDIMENTOS_DISTINTOS', 'SCORE_OUTLIER']]
          .head(15).to_string(index=False))
    print("=" * 80)

    caminho_csv = dir_saida / f"perfis_estabelecimentos_hdbscan_{args.uf.lower()}_{args.ano}.csv"
    perfil.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Perfis completos salvos em: '{caminho_csv}'")

    gerar_grafico(perfil, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE CLUSTERS E OUTLIERS (HDBSCAN) CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecta clusters naturais e estabelecimentos atípicos com HDBSCAN.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--producao-minima", type=int, default=100, help="Volume mínimo de produção para um estabelecimento entrar na análise.")
    parser.add_argument("--min-cluster-size", type=int, default=5, help="Tamanho mínimo de cluster para o HDBSCAN.")
    parser.add_argument("--dir_saida", type=str, default="outputs/hdbscan_estabelecimentos", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
