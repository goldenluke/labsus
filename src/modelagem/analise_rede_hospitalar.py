# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE REDES COMPLEXAS APLICADA AO FLUXO DE PACIENTES
======================================================================
Este script modela a rede de referência de pacientes como um grafo
matemático, calcula métricas de centralidade e gera uma visualização
estática da rede.
"""

import pandas as pd
from pathlib import Path
import argparse
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np # Importado para a normalização

def carregar_dados_de_fluxo(caminho_fluxo_csv: Path):
    """Carrega o painel de dados de fluxo de pacientes."""
    print("\n--- [ETAPA 1] Carregando dados de fluxo de pacientes ---")
    try:
        df_fluxo = pd.read_csv(caminho_fluxo_csv, sep=';', dtype=str)
        df_fluxo['N_PACIENTES'] = pd.to_numeric(df_fluxo['N_PACIENTES'], errors='coerce')
        df_fluxo.dropna(subset=['MUNIC_RES', 'MUNIC_MOV', 'N_PACIENTES'], inplace=True)
        print(f"✅ Dados de fluxo carregados com {len(df_fluxo)} rotas.")
        return df_fluxo
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo de fluxo não encontrado em '{caminho_fluxo_csv}'.")
        return None

def construir_e_analisar_rede(df_fluxo: pd.DataFrame, dir_saida: Path, nome_base_arquivo: str):
    """Constrói o grafo, calcula as métricas e retorna ambos."""
    print("\n--- [ETAPA 2] Construindo o grafo da rede de saúde ---")

    G = nx.DiGraph()
    for index, row in df_fluxo.iterrows():
        G.add_edge(row['MUNIC_RES'], row['MUNIC_MOV'], weight=row['N_PACIENTES'])

    print(f"✅ Grafo construído com {G.number_of_nodes()} nós e {G.number_of_edges()} arestas.")

    caminho_gephi = dir_saida / f"rede_para_gephi_{nome_base_arquivo}.graphml"
    nx.write_graphml(G, caminho_gephi)
    print(f"\n✨ Arquivo para Gephi salvo em: {caminho_gephi}")

    print("\n--- [ETAPA 3] Calculando métricas de centralidade ---")

    in_degree = dict(G.in_degree(weight='weight'))
    out_degree = dict(G.out_degree(weight='weight'))
    betweenness = nx.betweenness_centrality(G, weight='weight', normalized=True)

    df_metricas = pd.DataFrame.from_dict(in_degree, orient='index', columns=['pacientes_recebidos'])
    df_metricas['pacientes_enviados'] = df_metricas.index.map(out_degree)
    df_metricas['centralidade_intermediacao'] = df_metricas.index.map(betweenness)
    df_metricas.fillna(0, inplace=True)
    df_metricas.index.name = 'CODMUNRES_6DIG'

    print("✅ Métricas de rede consolidadas com sucesso.")
    return G, df_metricas.sort_values('pacientes_recebidos', ascending=False)

# ==========================================================
# --- FUNÇÃO DE VISUALIZAÇÃO APRIMORADA ---
# ==========================================================
def visualizar_rede(G, df_metricas, dir_saida: Path, nome_base_arquivo: str):
    """Gera e salva uma visualização estática e aprimorada do grafo da rede."""
    print("\n--- [ETAPA 4] Gerando visualização da rede ---")

    if not G.nodes():
        print("⚠️ Rede vazia, impossível gerar visualização.")
        return

    fig, ax = plt.subplots(figsize=(25, 25))

    # --- LÓGICA DE TAMANHO APRIMORADA ---
    # Define um tamanho mínimo e máximo para os nós serem visíveis
    min_size = 50
    max_size = 5000

    # Pega os valores de pacientes recebidos
    sizes = np.array([df_metricas.loc[node]['pacientes_recebidos'] for node in G.nodes()])

    # Normaliza os tamanhos para o intervalo [0, 1] e depois escala para [min_size, max_size]
    if sizes.max() > sizes.min():
        node_sizes = min_size + (sizes - sizes.min()) / (sizes.max() - sizes.min()) * (max_size - min_size)
    else:
        node_sizes = [min_size] * len(G.nodes()) # Se todos tiverem o mesmo tamanho
    # --- FIM DA LÓGICA DE TAMANHO ---

    node_colors = [df_metricas.loc[node]['centralidade_intermediacao'] for node in G.nodes()]

    pos = nx.spring_layout(G, k=0.8, iterations=50, seed=42)

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes.tolist(), node_color=node_colors,
                           cmap=plt.cm.viridis, alpha=0.9, ax=ax)

    # Aumentando a visibilidade das arestas
    nx.draw_networkx_edges(G, pos, alpha=0.2, edge_color='gray', ax=ax)

    ax.set_title("Visualização da Rede de Fluxo de Pacientes", fontsize=30)

    sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=plt.Normalize(vmin=min(node_colors), vmax=max(node_colors)))
    sm.set_array([])

    cbar = fig.colorbar(sm, ax=ax, shrink=0.5)
    cbar.set_label('Centralidade de Intermediação', rotation=270, labelpad=25, fontsize=16)

    plt.axis('off')

    caminho_fig = dir_saida / f"mapa_rede_{nome_base_arquivo}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"🗺️  Mapa da rede salvo em: {caminho_fig}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analisa o fluxo de pacientes como uma rede complexa e calcula métricas de centralidade.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--fluxo-csv",
        type=str,
        required=True,
        help="Caminho para o arquivo CSV de fluxo de pacientes gerado por 'analise_fluxo_pacientes.py'."
    )
    parser.add_argument(
        "--dir_saida",
        type=str,
        default="outputs/analise_rede",
        help="Diretório para salvar o relatório de métricas da rede."
    )

    args = parser.parse_args()
    output_dir = Path(args.dir_saida)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_fluxo_pacientes = carregar_dados_de_fluxo(Path(args.fluxo_csv))

    if df_fluxo_pacientes is not None and not df_fluxo_pacientes.empty:
        nome_base_arquivo = Path(args.fluxo_csv).stem
        G, df_resultados_rede = construir_e_analisar_rede(df_fluxo_pacientes, output_dir, nome_base_arquivo)

        if not df_resultados_rede.empty:
            nome_arquivo_saida = f"metricas_rede_{nome_base_arquivo}.csv"
            caminho_csv = output_dir / nome_arquivo_saida

            df_resultados_rede.to_csv(caminho_csv, index=True, sep=';', encoding='utf-8-sig')

            print(f"\n📄 Relatório com as métricas da rede salvo em: '{caminho_csv}'")
            print("\n--- Amostra do Top 10 Municípios (Polos de Atendimento) ---")
            print(df_resultados_rede.head(10))

            visualizar_rede(G, df_resultados_rede, output_dir, nome_base_arquivo)

            print("\n" + "="*80)
            print("🎉 PIPELINE DE ANÁLISE DE REDE CONCLUÍDO! 🎉")
            print("="*80)
