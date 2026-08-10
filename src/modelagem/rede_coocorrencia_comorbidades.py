# -*- coding: utf-8 -*-
"""
======================================================================
  REDE DE COOCORRÊNCIA DE COMORBIDADES (SIH)
======================================================================
Este script constrói um grafo em que cada NÓ é uma categoria de CID-10
(3 caracteres, ex: "I50", "E11") e cada ARESTA liga duas categorias que
aparecem JUNTAS na mesma internação (diagnóstico principal + diagnósticos
secundários de uma mesma AIH) — revelando quais doenças costumam
"andar juntas" na população internada. Detecção de comunidades (Louvain)
agrupa as categorias em "constelações" de comorbidades que coocorrem mais
entre si do que com o resto da rede — útil para desenhar linhas de
cuidado integradas (ex: "constelação cardiometabólica": diabetes +
hipertensão + insuficiência cardíaca + doença renal).
"""

import argparse
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd
from networkx.algorithms.community import louvain_communities

from pysus.online_data.SIH import download as download_sih

COLUNAS_DIAGNOSTICO_SECUNDARIO = [f'DIAGSEC{i}' for i in range(1, 10)]


def carregar_internacoes(uf: str, anos: list, cid_coorte_prefixos: list = None) -> pd.DataFrame:
    dfs = []
    for ano in anos:
        print(f"[LOG] Baixando SIH para {uf}/{ano}...")
        downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
        df_ano = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
        dfs.append(df_ano)
    df = pd.concat(dfs, ignore_index=True)
    if cid_coorte_prefixos:
        df = df[df['DIAG_PRINC'].astype(str).str.startswith(tuple(cid_coorte_prefixos))]
    return df


def extrair_conjuntos_diagnosticos(df: pd.DataFrame, n_caracteres_cid: int = 3) -> list:
    """Para cada AIH, retorna o conjunto (sem repetição) de categorias de CID
    (diagnóstico principal + secundários) presentes."""
    colunas_presentes = ['DIAG_PRINC'] + [c for c in COLUNAS_DIAGNOSTICO_SECUNDARIO if c in df.columns]
    conjuntos = []
    for _, row in df[colunas_presentes].iterrows():
        codigos = set()
        for col in colunas_presentes:
            valor = row[col]
            if pd.notna(valor) and str(valor).strip() not in ('', '0', '0000'):
                codigos.add(str(valor).strip().upper()[:n_caracteres_cid])
        if len(codigos) >= 2:
            conjuntos.append(codigos)
    return conjuntos


def construir_grafo_coocorrencia(conjuntos_diagnosticos: list, min_frequencia_no: int, min_peso_aresta: int) -> nx.Graph:
    from collections import Counter

    contagem_nos = Counter()
    contagem_arestas = Counter()
    for codigos in conjuntos_diagnosticos:
        contagem_nos.update(codigos)
        for par in combinations(sorted(codigos), 2):
            contagem_arestas[par] += 1

    nos_frequentes = {codigo for codigo, freq in contagem_nos.items() if freq >= min_frequencia_no}

    G = nx.Graph()
    for codigo in nos_frequentes:
        G.add_node(codigo, frequencia=contagem_nos[codigo])
    for (a, b), peso in contagem_arestas.items():
        if a in nos_frequentes and b in nos_frequentes and peso >= min_peso_aresta:
            G.add_edge(a, b, weight=peso)

    G.remove_nodes_from(list(nx.isolates(G)))
    return G


def gerar_visualizacao(G: nx.Graph, comunidades: list, cid_coorte_nome: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    mapa_comunidade = {no: i for i, com in enumerate(comunidades) for no in com}
    cores_comunidade = [mapa_comunidade.get(no, -1) for no in G.nodes()]
    tamanhos = [80 + G.nodes[no]['frequencia'] * 2 for no in G.nodes()]
    larguras = [0.3 + G[u][v]['weight'] * 0.05 for u, v in G.edges()]

    pos = nx.spring_layout(G, k=0.6, seed=42, iterations=100)
    fig, ax = plt.subplots(figsize=(16, 16))
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=larguras, edge_color='gray', ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=tamanhos, node_color=cores_comunidade, cmap=cm.tab20, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)
    ax.set_title(f"Rede de Coocorrência de Comorbidades — {cid_coorte_nome} em {uf}\n(cor = comunidade detectada via Louvain)", fontsize=16)
    ax.axis('off')
    caminho_fig = dir_saida / f"rede_comorbidades_{cid_coorte_nome.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"🕸️ Visualização da rede salva em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    cid_nome = "Todos os Diagnósticos" if not args.cid_coorte else "-".join(args.cid_coorte)

    print(f"\n--- [ETAPA 1] Carregando internações em {args.uf}/{args.anos} ---")
    df = carregar_internacoes(args.uf, args.anos, args.cid_coorte)
    print(f"✅ {len(df)} internações carregadas.")

    print(f"\n--- [ETAPA 2] Extraindo conjuntos de diagnósticos coocorrentes por AIH ---")
    conjuntos = extrair_conjuntos_diagnosticos(df)
    print(f"✅ {len(conjuntos)} internações com 2+ diagnósticos (candidatas à coocorrência).")

    if len(conjuntos) < 30:
        print("❌ Poucas internações com múltiplos diagnósticos para uma rede confiável (mínimo recomendado: 30).")
        return

    print(f"\n--- [ETAPA 3] Construindo o grafo de coocorrência ---")
    G = construir_grafo_coocorrencia(conjuntos, args.min_frequencia_no, args.min_peso_aresta)
    print(f"✅ Grafo com {G.number_of_nodes()} categorias (nós) e {G.number_of_edges()} coocorrências (arestas).")

    if G.number_of_nodes() < 3:
        print("❌ Rede muito pequena após filtros de frequência mínima. Tente reduzir --min-frequencia-no / --min-peso-aresta.")
        return

    print(f"\n--- [ETAPA 4] Detectando comunidades (Louvain) ---")
    comunidades = louvain_communities(G, weight='weight', seed=42)
    print(f"✅ {len(comunidades)} comunidades de comorbidades detectadas.")

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: COMUNIDADES DE COMORBIDADES — {cid_nome} EM {args.uf} ---")
    print("=" * 80)
    linhas_relatorio = []
    for i, com in enumerate(sorted(comunidades, key=len, reverse=True)):
        membros = sorted(com, key=lambda n: -G.nodes[n]['frequencia'])
        print(f"\nComunidade {i + 1} ({len(com)} categorias): {', '.join(membros[:15])}{' ...' if len(membros) > 15 else ''}")
        for m in membros:
            linhas_relatorio.append({'CATEGORIA_CID': m, 'COMUNIDADE': i + 1, 'FREQUENCIA': G.nodes[m]['frequencia']})
    print("=" * 80)

    caminho_csv = dir_saida / f"comunidades_comorbidades_{cid_nome.lower().replace(' ', '_')}_{args.uf.lower()}.csv"
    pd.DataFrame(linhas_relatorio).sort_values(['COMUNIDADE', 'FREQUENCIA'], ascending=[True, False]).to_csv(
        caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Comunidades salvas em: '{caminho_csv}'")

    gerar_visualizacao(G, comunidades, cid_nome, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE REDE DE COMORBIDADES CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Constrói uma rede de coocorrência de comorbidades a partir do SIH.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SIH a usar.")
    parser.add_argument("--cid-coorte", nargs="+", default=None, help="Prefixos de CID-10 para restringir a uma coorte de diagnóstico principal (opcional; ex: I50 para insuficiência cardíaca).")
    parser.add_argument("--min-frequencia-no", type=int, default=20, help="Frequência mínima de uma categoria de CID para entrar na rede.")
    parser.add_argument("--min-peso-aresta", type=int, default=5, help="Nº mínimo de coocorrências para manter uma aresta.")
    parser.add_argument("--dir_saida", type=str, default="outputs/rede_comorbidades", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
