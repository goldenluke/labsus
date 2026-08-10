# -*- coding: utf-8 -*-
"""
======================================================================
  CLUSTERS ESPACIAIS LOCAIS (LISA) DE UM AGRAVO DO SINAN
======================================================================
Este script calcula o Índice de Moran Local (LISA — Local Indicators of
Spatial Association) para a taxa de incidência/notificação de um agravo
do SINAN por município, classificando cada município em um dos quatro
quadrantes espaciais:
  - Alto-Alto (HH): foco de risco elevado cercado por vizinhos de risco elevado
  - Baixo-Baixo (LL): área de baixo risco cercada por vizinhos de baixo risco
  - Alto-Baixo / Baixo-Alto (outliers espaciais): município destoa dos vizinhos

Diferente do Moran global (que dá um único número para toda a UF), o LISA
aponta EXATAMENTE QUAIS municípios formam os clusters — é a ferramenta
clássica de vigilância epidemiológica para focar investigação de campo.
"""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
from libpysal.weights import Queen
from esda.moran import Moran_Local

QUADRANTE_NOMES = {1: 'Alto-Alto', 2: 'Baixo-Alto', 3: 'Baixo-Baixo', 4: 'Alto-Baixo'}
QUADRANTE_CORES = {1: '#d73027', 2: '#91bfdb', 3: '#4575b4', 4: '#fc8d59'}


def carregar_geojson_uf(diretorio_geojson: Path, uf: str) -> gpd.GeoDataFrame:
    mapa_arquivos = {
        'AC': 'geojs-12-mun.json', 'AL': 'geojs-27-mun.json', 'AM': 'geojs-13-mun.json', 'AP': 'geojs-16-mun.json',
        'BA': 'geojs-29-mun.json', 'CE': 'geojs-23-mun.json', 'DF': 'geojs-53-mun.json', 'ES': 'geojs-32-mun.json',
        'GO': 'geojs-52-mun.json', 'MA': 'geojs-21-mun.json', 'MG': 'geojs-31-mun.json', 'MS': 'geojs-50-mun.json',
        'MT': 'geojs-51-mun.json', 'PA': 'geojs-15-mun.json', 'PB': 'geojs-25-mun.json', 'PE': 'geojs-26-mun.json',
        'PI': 'geojs-22-mun.json', 'PR': 'geojs-41-mun.json', 'RJ': 'geojs-33-mun.json', 'RN': 'geojs-24-mun.json',
        'RO': 'geojs-11-mun.json', 'RR': 'geojs-14-mun.json', 'RS': 'geojs-43-mun.json', 'SC': 'geojs-42-mun.json',
        'SE': 'geojs-28-mun.json', 'SP': 'geojs-35-mun.json', 'TO': 'geojs-17-mun.json',
    }
    nome_arquivo = mapa_arquivos.get(uf.upper())
    if not nome_arquivo:
        raise ValueError(f"UF '{uf}' não reconhecida.")
    gdf = gpd.read_file(diretorio_geojson / nome_arquivo)
    gdf['CODMUN_6DIG'] = gdf['id'].astype(str).str[:6]
    return gdf


def carregar_taxa_agravo(dis_code: str, uf: str, ano: int, arquivo_populacao: Path) -> pd.DataFrame:
    """Baixa o agravo do SINAN e calcula a taxa por 100 mil habitantes por município (reaproveita a
    lógica já validada em src/utils/dataloaders.py::processar_agravo_sinan_generico)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.dataloaders import processar_agravo_sinan_generico

    df = processar_agravo_sinan_generico(
        ufs=[uf], anos=[ano], arquivo_populacao=arquivo_populacao,
        dis_code=dis_code, nome_indicador='TAXA_AGRAVO',
    )
    if df is None or df.empty:
        return pd.DataFrame()
    return df[['cod_mun_ibge_6', 'TAXA_AGRAVO']]


def calcular_lisa(gdf: gpd.GeoDataFrame, coluna_valor: str, permutacoes: int = 999):
    w = Queen.from_dataframe(gdf, use_index=False)
    w.transform = 'r'
    lisa = Moran_Local(gdf[coluna_valor].values, w, permutations=permutacoes, seed=42)
    return lisa


def gerar_mapa_lisa(gdf: gpd.GeoDataFrame, dis_code: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(color=gdf['LISA_COR'], ax=ax, edgecolor='0.6', linewidth=0.4)
    ax.set_title(f"Clusters Espaciais Locais (LISA) — SINAN/{dis_code} em {uf}", fontsize=15)
    ax.axis('off')
    legendas = [mpatches.Patch(color=cor, label=nome) for _, (nome, cor) in
                {q: (QUADRANTE_NOMES[q], QUADRANTE_CORES[q]) for q in QUADRANTE_NOMES}.items()]
    legendas.append(mpatches.Patch(color='#cccccc', label='Não significante'))
    ax.legend(handles=legendas, loc='lower left', fontsize=9)
    caminho_fig = dir_saida / f"mapa_lisa_{dis_code.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"🗺️ Mapa LISA salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Calculando taxa de SINAN/{args.dis_code} por município em {args.uf}/{args.ano} ---")
    df_taxa = carregar_taxa_agravo(args.dis_code, args.uf, args.ano, Path(args.populacao))
    if df_taxa.empty:
        print("❌ Nenhum dado de taxa disponível. Abortando.")
        return
    print(f"✅ Taxa calculada para {len(df_taxa)} municípios.")

    print(f"\n--- [ETAPA 2] Carregando geometria dos municípios de {args.uf} ---")
    gdf = carregar_geojson_uf(Path(args.geojson_dir), args.uf)
    gdf_merged = gdf.merge(df_taxa, left_on='CODMUN_6DIG', right_on='cod_mun_ibge_6', how='inner')
    gdf_merged = gdf_merged.dropna(subset=['TAXA_AGRAVO']).reset_index(drop=True)

    if len(gdf_merged) < 5:
        print("❌ Poucos municípios com dados para uma análise LISA confiável (mínimo recomendado: 5).")
        return

    print(f"\n--- [ETAPA 3] Calculando LISA (Moran Local, permutações={args.permutacoes}) ---")
    lisa = calcular_lisa(gdf_merged, 'TAXA_AGRAVO', args.permutacoes)

    gdf_merged['LISA_I'] = lisa.Is
    gdf_merged['LISA_P_VALOR'] = lisa.p_sim
    gdf_merged['LISA_QUADRANTE'] = lisa.q
    gdf_merged['LISA_SIGNIFICANTE'] = lisa.p_sim < args.significancia
    gdf_merged['LISA_CLASSIFICACAO'] = gdf_merged.apply(
        lambda r: QUADRANTE_NOMES[r['LISA_QUADRANTE']] if r['LISA_SIGNIFICANTE'] else 'Não significante', axis=1
    )
    gdf_merged['LISA_COR'] = gdf_merged.apply(
        lambda r: QUADRANTE_CORES[r['LISA_QUADRANTE']] if r['LISA_SIGNIFICANTE'] else '#cccccc', axis=1
    )

    n_hh = (gdf_merged['LISA_CLASSIFICACAO'] == 'Alto-Alto').sum()
    print("\n" + "=" * 70)
    print(f"--- RESULTADO: CLUSTERS LOCAIS DE SINAN/{args.dis_code} EM {args.uf} ---")
    print("=" * 70)
    print(gdf_merged['LISA_CLASSIFICACAO'].value_counts().to_string())
    print(f"\n⚠️ {n_hh} município(s) identificado(s) como foco 'Alto-Alto' (cluster de risco elevado, prioridade para investigação).")
    print("=" * 70)

    colunas_relatorio = ['CODMUN_6DIG', 'name', 'TAXA_AGRAVO', 'LISA_I', 'LISA_P_VALOR', 'LISA_CLASSIFICACAO']
    colunas_relatorio = [c for c in colunas_relatorio if c in gdf_merged.columns]
    df_relatorio = pd.DataFrame(gdf_merged[colunas_relatorio]).sort_values('TAXA_AGRAVO', ascending=False)
    caminho_csv = dir_saida / f"lisa_{args.dis_code.lower()}_{args.uf.lower()}_{args.ano}.csv"
    df_relatorio.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Relatório com classificação por município salvo em: '{caminho_csv}'")

    gerar_mapa_lisa(gdf_merged, args.dis_code, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE LISA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula clusters espaciais locais (LISA) para um agravo do SINAN.")
    parser.add_argument("--dis-code", type=str, required=True, help="Código do agravo do SINAN (ex: DENG, CHIK, ANIM, HANS).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada.")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os GeoJSON de municípios.")
    parser.add_argument("--significancia", type=float, default=0.05, help="Limiar de p-valor para considerar um cluster significante.")
    parser.add_argument("--permutacoes", type=int, default=999, help="Número de permutações do teste de significância.")
    parser.add_argument("--dir_saida", type=str, default="outputs/lisa_sinan", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
