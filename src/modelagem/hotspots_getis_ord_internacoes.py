# -*- coding: utf-8 -*-
"""
======================================================================
  HOTSPOTS ESPACIAIS (GETIS-ORD Gi*) DE TAXA DE INTERNAÇÃO
======================================================================
Este script identifica hotspots (concentrações estatisticamente
significantes de alta taxa) e coldspots (concentrações de baixa taxa) de
internação hospitalar por uma causa configurável (prefixo de CID-10),
usando a estatística Gi* de Getis-Ord — a ferramenta clássica de
"criminologia espacial"/vigilância em saúde para responder: "onde estão
os agrupamentos geográficos estatisticamente anômalos?", distinta do
LISA (que classifica em quadrantes Alto-Alto/Baixo-Baixo) por focar
diretamente na intensidade e significância local do agrupamento.
"""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
from libpysal.weights import Queen
from esda.getisord import G_Local

from pysus.online_data.SIH import download as download_sih


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


def carregar_taxa_internacao(uf: str, ano: int, cid_prefixos: list, arquivo_populacao: Path) -> pd.DataFrame:
    """Baixa o SIH/RD, filtra por prefixo(s) de CID-10 e calcula a taxa de internação
    por 100 mil habitantes, por município de RESIDÊNCIA."""
    print(f"[LOG] Baixando SIH para {uf}/{ano}...")
    downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
    if isinstance(downloaded, list):
        if not downloaded:
            return pd.DataFrame()
        df_sih = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True)
    else:
        df_sih = downloaded.to_dataframe()

    df_diag = df_sih[df_sih['DIAG_PRINC'].astype(str).str.startswith(tuple(cid_prefixos))].copy()
    df_diag['MUNIC_RES_6DIG'] = df_diag['MUNIC_RES'].astype(str).str[:6]
    casos = df_diag.groupby('MUNIC_RES_6DIG').size().rename('N_INTERNACOES')

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.dataloaders import filtrar_populacao

    df_pop = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
    if df_pop is None:
        return pd.DataFrame()

    df_taxa = df_pop.join(casos, how='left')
    df_taxa['N_INTERNACOES'] = df_taxa['N_INTERNACOES'].fillna(0)
    df_taxa['TAXA_INTERNACAO_10K'] = (df_taxa['N_INTERNACOES'] / df_taxa['populacao']) * 10000
    df_taxa = df_taxa.reset_index().rename(columns={'index': 'cod_mun_ibge_6'})
    return df_taxa[['cod_mun_ibge_6', 'N_INTERNACOES', 'TAXA_INTERNACAO_10K']]


def calcular_getis_ord(gdf: gpd.GeoDataFrame, coluna_valor: str, permutacoes: int = 999):
    w = Queen.from_dataframe(gdf, use_index=False)
    g = G_Local(gdf[coluna_valor].values, w, star=True, permutations=permutacoes, seed=42)
    return g


def classificar_hotspot(z, p, alfa=0.05):
    if p >= alfa:
        return 'Não significante'
    return 'Hotspot (alto)' if z > 0 else 'Coldspot (baixo)'


def gerar_mapa_hotspots(gdf: gpd.GeoDataFrame, cid_nome: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    cores = {'Hotspot (alto)': '#d73027', 'Coldspot (baixo)': '#4575b4', 'Não significante': '#e0e0e0'}
    fig, ax = plt.subplots(figsize=(10, 10))
    gdf['COR'] = gdf['HOTSPOT_CLASSIFICACAO'].map(cores)
    gdf.plot(color=gdf['COR'], ax=ax, edgecolor='0.6', linewidth=0.4)
    ax.set_title(f"Hotspots de Internação (Getis-Ord Gi*) — {cid_nome} em {uf}", fontsize=14)
    ax.axis('off')
    import matplotlib.patches as mpatches
    legendas = [mpatches.Patch(color=c, label=l) for l, c in cores.items()]
    ax.legend(handles=legendas, loc='lower left', fontsize=9)
    caminho_fig = dir_saida / f"mapa_hotspots_{cid_nome.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"🗺️ Mapa de hotspots salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    cid_nome = "-".join(args.cids)

    print(f"\n--- [ETAPA 1] Calculando taxa de internação por '{cid_nome}' em {args.uf}/{args.ano} ---")
    df_taxa = carregar_taxa_internacao(args.uf, args.ano, args.cids, Path(args.populacao))
    if df_taxa.empty:
        print("❌ Nenhum dado disponível. Abortando.")
        return
    print(f"✅ Taxa calculada para {len(df_taxa)} municípios.")

    print(f"\n--- [ETAPA 2] Carregando geometria dos municípios de {args.uf} ---")
    gdf = carregar_geojson_uf(Path(args.geojson_dir), args.uf)
    gdf_merged = gdf.merge(df_taxa, left_on='CODMUN_6DIG', right_on='cod_mun_ibge_6', how='inner')
    gdf_merged = gdf_merged.reset_index(drop=True)

    if len(gdf_merged) < 5:
        print("❌ Poucos municípios para uma análise Getis-Ord confiável (mínimo recomendado: 5).")
        return

    print(f"\n--- [ETAPA 3] Calculando estatística Gi* (permutações={args.permutacoes}) ---")
    g = calcular_getis_ord(gdf_merged, 'TAXA_INTERNACAO_10K', args.permutacoes)
    gdf_merged['GI_Z'] = g.Zs
    gdf_merged['GI_P_VALOR'] = g.p_sim
    gdf_merged['HOTSPOT_CLASSIFICACAO'] = [classificar_hotspot(z, p, args.significancia) for z, p in zip(g.Zs, g.p_sim)]

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: HOTSPOTS DE INTERNAÇÃO POR '{cid_nome}' EM {args.uf} ---")
    print("=" * 70)
    print(gdf_merged['HOTSPOT_CLASSIFICACAO'].value_counts().to_string())
    print("=" * 70)

    colunas_relatorio = ['CODMUN_6DIG', 'name', 'N_INTERNACOES', 'TAXA_INTERNACAO_10K', 'GI_Z', 'GI_P_VALOR', 'HOTSPOT_CLASSIFICACAO']
    colunas_relatorio = [c for c in colunas_relatorio if c in gdf_merged.columns]
    df_relatorio = pd.DataFrame(gdf_merged[colunas_relatorio]).sort_values('GI_Z', ascending=False)
    caminho_csv = dir_saida / f"hotspots_{cid_nome.lower()}_{args.uf.lower()}_{args.ano}.csv"
    df_relatorio.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Relatório com classificação por município salvo em: '{caminho_csv}'")

    gerar_mapa_hotspots(gdf_merged, cid_nome, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE HOTSPOTS CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Identifica hotspots/coldspots espaciais de internação (Getis-Ord Gi*).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--cids", nargs="+", default=['J45'], help="Prefixos de CID-10 a considerar (ex: J45 para asma).")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada.")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os GeoJSON de municípios.")
    parser.add_argument("--significancia", type=float, default=0.05, help="Limiar de p-valor para considerar um hotspot/coldspot significante.")
    parser.add_argument("--permutacoes", type=int, default=999, help="Número de permutações do teste de significância.")
    parser.add_argument("--dir_saida", type=str, default="outputs/hotspots_internacao", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
