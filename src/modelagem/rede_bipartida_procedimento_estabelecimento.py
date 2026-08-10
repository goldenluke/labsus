# -*- coding: utf-8 -*-
"""
======================================================================
  REDE BIPARTIDA PROCEDIMENTO x ESTABELECIMENTO (SIA) E CLUSTERS DE
  ESPECIALIZAÇÃO DA REDE DE SAÚDE
======================================================================
Este script constrói um grafo BIPARTIDO a partir da produção ambulatorial
(SIA/PA): de um lado, ESTABELECIMENTOS (PA_CODUNI); do outro,
PROCEDIMENTOS (PA_PROC_ID); uma aresta liga um estabelecimento a um
procedimento se ele o realizou no período. Em seguida, PROJETA esse grafo
bipartido em uma rede UNIPARTIDA de estabelecimentos, onde dois
estabelecimentos ficam conectados com peso proporcional ao número de
procedimentos EM COMUM que realizam — e aplica detecção de comunidades
(Louvain) para identificar "clusters de especialização": grupos de
estabelecimentos com portfólio de serviços parecido, útil para
planejamento de regionalização e identificação de lacunas de oferta.
"""

import argparse
from pathlib import Path

import networkx as nx
import pandas as pd
from networkx.algorithms import bipartite
from networkx.algorithms.community import louvain_communities

from pysus.online_data.SIA import download as download_sia


def carregar_producao_ambulatorial(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SIA/PA para {uf}/{ano}...")
    downloaded = download_sia(states=uf, years=ano, months=list(range(1, 13)), groups=['PA'])
    if isinstance(downloaded, list):
        df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True)
    else:
        df = downloaded.to_dataframe()
    return df


def construir_grafo_bipartido(df: pd.DataFrame, min_producao_procedimento: int, min_producao_estabelecimento: int) -> tuple:
    df = df[['PA_CODUNI', 'PA_PROC_ID']].dropna().astype(str)

    contagem_proc = df['PA_PROC_ID'].value_counts()
    procedimentos_validos = set(contagem_proc[contagem_proc >= min_producao_procedimento].index)
    contagem_estab = df['PA_CODUNI'].value_counts()
    estabelecimentos_validos = set(contagem_estab[contagem_estab >= min_producao_estabelecimento].index)

    df_filtrado = df[df['PA_PROC_ID'].isin(procedimentos_validos) & df['PA_CODUNI'].isin(estabelecimentos_validos)]
    pares_unicos = df_filtrado.drop_duplicates()

    B = nx.Graph()
    estabelecimentos = set(pares_unicos['PA_CODUNI'])
    procedimentos = set(pares_unicos['PA_PROC_ID'])
    B.add_nodes_from(estabelecimentos, bipartite=0)
    B.add_nodes_from(procedimentos, bipartite=1)
    B.add_edges_from(pares_unicos.itertuples(index=False, name=None))
    return B, estabelecimentos


def gerar_visualizacao(G_proj: nx.Graph, comunidades: list, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    mapa_comunidade = {no: i for i, com in enumerate(comunidades) for no in com}
    cores = [mapa_comunidade.get(no, -1) for no in G_proj.nodes()]
    graus = dict(G_proj.degree(weight='weight'))
    tamanhos = [30 + graus.get(no, 0) * 3 for no in G_proj.nodes()]

    pos = nx.spring_layout(G_proj, k=0.4, seed=42, iterations=80)
    fig, ax = plt.subplots(figsize=(16, 16))
    pesos = [G_proj[u][v]['weight'] for u, v in G_proj.edges()]
    max_peso = max(pesos) if pesos else 1
    larguras = [0.2 + 2 * (w / max_peso) for w in pesos]
    nx.draw_networkx_edges(G_proj, pos, alpha=0.15, width=larguras, edge_color='gray', ax=ax)
    nx.draw_networkx_nodes(G_proj, pos, node_size=tamanhos, node_color=cores, cmap=cm.tab20, ax=ax)
    ax.set_title(f"Clusters de Especialização da Rede Ambulatorial — {uf}\n(cor = comunidade / perfil de portfólio de procedimentos)", fontsize=16)
    ax.axis('off')
    caminho_fig = dir_saida / f"rede_especializacao_estabelecimentos_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"🕸️ Visualização da rede salva em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando produção ambulatorial (SIA) para {args.uf}/{args.ano} ---")
    df = carregar_producao_ambulatorial(args.uf, args.ano)
    print(f"✅ {len(df)} registros de produção carregados.")

    print(f"\n--- [ETAPA 2] Construindo grafo bipartido Procedimento x Estabelecimento ---")
    B, estabelecimentos = construir_grafo_bipartido(df, args.min_producao_procedimento, args.min_producao_estabelecimento)
    print(f"✅ Grafo bipartido com {len(estabelecimentos)} estabelecimentos e {B.number_of_nodes() - len(estabelecimentos)} procedimentos.")

    if len(estabelecimentos) < 5:
        print("❌ Poucos estabelecimentos após os filtros de produção mínima. Reduza --min-producao-estabelecimento/--min-producao-procedimento.")
        return

    print(f"\n--- [ETAPA 3] Projetando rede de estabelecimentos (similaridade de portfólio) ---")
    G_proj = bipartite.weighted_projected_graph(B, estabelecimentos)
    G_proj.remove_nodes_from(list(nx.isolates(G_proj)))
    print(f"✅ Rede projetada com {G_proj.number_of_nodes()} estabelecimentos e {G_proj.number_of_edges()} conexões (procedimentos em comum).")

    print(f"\n--- [ETAPA 4] Detectando comunidades (clusters de especialização) ---")
    comunidades = louvain_communities(G_proj, weight='weight', seed=42)
    print(f"✅ {len(comunidades)} clusters de especialização detectados.")

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: CLUSTERS DE ESPECIALIZAÇÃO DA REDE AMBULATORIAL EM {args.uf} ---")
    print("=" * 80)
    linhas = []
    for i, com in enumerate(sorted(comunidades, key=len, reverse=True)):
        print(f"Cluster {i + 1}: {len(com)} estabelecimentos")
        for cnes in com:
            linhas.append({'PA_CODUNI': cnes, 'CLUSTER_ESPECIALIZACAO': i + 1})
    print("=" * 80)

    caminho_csv = dir_saida / f"clusters_especializacao_{args.uf.lower()}_{args.ano}.csv"
    pd.DataFrame(linhas).to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Clusters salvos em: '{caminho_csv}'")

    gerar_visualizacao(G_proj, comunidades, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE REDE BIPARTIDA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Constrói uma rede bipartida Procedimento x Estabelecimento (SIA) e detecta clusters de especialização.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--min-producao-procedimento", type=int, default=50, help="Produção mínima de um procedimento (nº de registros) para entrar na rede.")
    parser.add_argument("--min-producao-estabelecimento", type=int, default=50, help="Produção mínima de um estabelecimento (nº de registros) para entrar na rede.")
    parser.add_argument("--dir_saida", type=str, default="outputs/rede_bipartida_especializacao", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
