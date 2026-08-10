# -*- coding: utf-8 -*-
"""
======================================================================
  PERFIS TERRITORIAIS COM UMAP + HDBSCAN
======================================================================
Este script projeta o painel de indicadores municipais (dezenas de
indicadores de saúde simultâneos) em um mapa 2D usando UMAP (Uniform
Manifold Approximation and Projection) — uma técnica de redução de
dimensionalidade não-linear mais capaz de preservar a estrutura de
vizinhança "real" dos dados do que PCA, e mais estável/interpretável do
que t-SNE para agrupamento subsequente — e então aplica HDBSCAN sobre
essa projeção para encontrar perfis territoriais naturais.

Diferente do K-Means usado em `clusters.py` (que assume clusters
esféricos de tamanho parecido, exige k pré-definido e classifica TODOS os
municípios em algum perfil), esta combinação captura estruturas de
vizinhança não-lineares e IDENTIFICA municípios "atípicos" (que não se
encaixam bem em nenhum perfil territorial) em vez de forçá-los a entrar
no perfil mais próximo.

Nota metodológica: por simplicidade, a mesma projeção 2D é usada tanto
para o clustering quanto para a visualização — uma prática comum em
análise exploratória, mas que pode distorcer densidades relativas; para
inferência mais rigorosa, o ideal seria fazer o UMAP para um número maior
de componentes e usar só uma projeção 2D separada para visualizar.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import umap
import hdbscan
from sklearn.preprocessing import StandardScaler


def carregar_painel(caminho_csv: Path, uf: list, ano: int, indicadores: list = None) -> pd.DataFrame:
    df = pd.read_csv(caminho_csv, sep=';', dtype={'cod_mun_ibge_6': str})
    if uf:
        df = df[df['UF'].isin(uf)]
    if ano:
        df = df[df['ANO'] == ano]

    if indicadores:
        colunas_indicadores = [c for c in indicadores if c in df.columns]
    else:
        numericas = df.select_dtypes(include=np.number).columns.tolist()
        colunas_indicadores = [c for c in numericas if c.isupper() and c not in ('ANO',)]

    if not colunas_indicadores:
        raise ValueError("Nenhuma coluna de indicador numérica identificada. Especifique com --indicadores.")

    df_final = df[['cod_mun_ibge_6', 'UF', 'municipio'] + colunas_indicadores].dropna()
    return df_final, colunas_indicadores


def projetar_e_agrupar(df: pd.DataFrame, colunas_indicadores: list, n_neighbors: int, min_dist: float, min_cluster_size: int, seed: int):
    X = df[colunas_indicadores].values
    X_scaled = StandardScaler().fit_transform(X)

    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, n_components=2, random_state=seed)
    embedding = reducer.fit_transform(X_scaled)
    df = df.copy()
    df['UMAP_1'], df['UMAP_2'] = embedding[:, 0], embedding[:, 1]

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
    df['PERFIL_TERRITORIAL'] = clusterer.fit_predict(embedding)
    df['E_ATIPICO'] = df['PERFIL_TERRITORIAL'] == -1
    return df


def descrever_perfis(df: pd.DataFrame, colunas_indicadores: list) -> pd.DataFrame:
    perfis_validos = df[df['PERFIL_TERRITORIAL'] != -1]
    return perfis_validos.groupby('PERFIL_TERRITORIAL')[colunas_indicadores].mean()


def gerar_grafico(df: pd.DataFrame, dir_saida: Path, contexto: str):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    plt.figure(figsize=(11, 9))
    normais = df[~df['E_ATIPICO']]
    atipicos = df[df['E_ATIPICO']]
    scatter = plt.scatter(normais['UMAP_1'], normais['UMAP_2'], c=normais['PERFIL_TERRITORIAL'], cmap=cm.tab10, s=40, alpha=0.7)
    plt.scatter(atipicos['UMAP_1'], atipicos['UMAP_2'], color='black', marker='x', s=70, label=f'Municípios atípicos (n={len(atipicos)})')
    plt.legend(*scatter.legend_elements(), title="Perfil", loc='upper right')
    plt.title(f"Perfis Territoriais (UMAP + HDBSCAN) — {contexto}")
    caminho_fig = dir_saida / f"umap_hdbscan_perfis_{contexto.lower().replace(' ', '_')}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Mapa de perfis territoriais salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    contexto = f"{'-'.join(args.ufs) if args.ufs else 'Brasil'} ({args.ano})"

    print(f"\n--- [ETAPA 1] Carregando painel de indicadores para {contexto} ---")
    df, colunas_indicadores = carregar_painel(Path(args.painel_csv), args.ufs, args.ano, args.indicadores)
    print(f"✅ {len(df)} municípios, {len(colunas_indicadores)} indicadores: {colunas_indicadores}")

    if len(df) < 15:
        print("❌ Poucos municípios para uma análise de UMAP/HDBSCAN confiável (mínimo recomendado: 15).")
        return

    print(f"\n--- [ETAPA 2] Projetando (UMAP) e agrupando (HDBSCAN) ---")
    df = projetar_e_agrupar(df, colunas_indicadores, args.n_neighbors, args.min_dist, args.min_cluster_size, args.seed)
    n_perfis = df[df['PERFIL_TERRITORIAL'] != -1]['PERFIL_TERRITORIAL'].nunique()
    n_atipicos = df['E_ATIPICO'].sum()

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: PERFIS TERRITORIAIS EM {contexto} ---")
    print("=" * 80)
    print(f"{n_perfis} perfis territoriais naturais detectados.")
    print(f"{n_atipicos} municípios ({n_atipicos / len(df):.1%}) identificados como atípicos.")
    print("\n--- Perfil médio de cada grupo (indicadores originais, não padronizados) ---")
    print(descrever_perfis(df, colunas_indicadores).round(2).to_string())
    print("=" * 80)

    caminho_csv = dir_saida / f"perfis_territoriais_{contexto.lower().replace(' ', '_').replace('(', '').replace(')', '')}.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Municípios com perfil atribuído salvos em: '{caminho_csv}'")

    gerar_grafico(df, dir_saida, contexto)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE PERFIS TERRITORIAIS (UMAP + HDBSCAN) CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Projeta (UMAP) e agrupa (HDBSCAN) municípios por perfil de indicadores de saúde.")
    parser.add_argument("--painel-csv", type=str, required=True, help="Caminho para o painel de indicadores (gerado por integrar_indicadores.py).")
    parser.add_argument("--ufs", nargs="+", default=None, help="Lista de UFs a incluir (opcional; se omitido, considera todas as UFs presentes no painel).")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--indicadores", nargs="+", default=None, help="Lista de indicadores a usar (opcional; se omitido, detecta automaticamente colunas numéricas em maiúsculas).")
    parser.add_argument("--n-neighbors", type=int, default=15, help="Parâmetro n_neighbors do UMAP.")
    parser.add_argument("--min-dist", type=float, default=0.1, help="Parâmetro min_dist do UMAP.")
    parser.add_argument("--min-cluster-size", type=int, default=5, help="Tamanho mínimo de cluster para o HDBSCAN.")
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatória.")
    parser.add_argument("--dir_saida", type=str, default="outputs/umap_hdbscan_perfis", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
