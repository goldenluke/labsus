# -*- coding: utf-8 -*-
"""
======================================================================
  DIFUSÃO ESPACIAL DE SURTO (SINAN) — PEQUENOS MÚLTIPLOS NO TEMPO
======================================================================
Diferente dos mapas de fluxo (origem->destino) e dos mapas de
autocorrelação espacial (um único retrato estático), este script mostra
COMO um agravo se espalhou geograficamente mês a mês: agrega as
notificações do SINAN por município e mês, e desenha uma grade de
mapas coropléticos (pequenos múltiplos) na mesma escala de cor, um por
mês, para visualizar a progressão espacial da epidemia. Também salva
uma série temporal (formato largo) com os municípios mais afetados,
que a interface renderiza como gráfico de linhas no Plotly.
"""

import argparse
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from pysus.ftp.databases.sinan import SINAN

MAPA_GEOJSON_UF = {
    'AC': 'geojs-12-mun.json', 'AL': 'geojs-27-mun.json', 'AM': 'geojs-13-mun.json', 'AP': 'geojs-16-mun.json',
    'BA': 'geojs-29-mun.json', 'CE': 'geojs-23-mun.json', 'DF': 'geojs-53-mun.json', 'ES': 'geojs-32-mun.json',
    'GO': 'geojs-52-mun.json', 'MA': 'geojs-21-mun.json', 'MG': 'geojs-31-mun.json', 'MS': 'geojs-50-mun.json',
    'MT': 'geojs-51-mun.json', 'PA': 'geojs-15-mun.json', 'PB': 'geojs-25-mun.json', 'PE': 'geojs-26-mun.json',
    'PI': 'geojs-22-mun.json', 'PR': 'geojs-41-mun.json', 'RJ': 'geojs-33-mun.json', 'RN': 'geojs-24-mun.json',
    'RO': 'geojs-11-mun.json', 'RR': 'geojs-14-mun.json', 'RS': 'geojs-43-mun.json', 'SC': 'geojs-42-mun.json',
    'SE': 'geojs-28-mun.json', 'SP': 'geojs-35-mun.json', 'TO': 'geojs-17-mun.json',
}


def carregar_geojson_uf(diretorio_geojson: Path, uf: str) -> gpd.GeoDataFrame:
    nome_arquivo = MAPA_GEOJSON_UF.get(uf.upper())
    if not nome_arquivo:
        raise ValueError(f"UF '{uf}' não reconhecida.")
    gdf = gpd.read_file(diretorio_geojson / nome_arquivo)
    gdf['CODMUN_6DIG'] = gdf['id'].astype(str).str[:6]
    return gdf


def carregar_notificacoes(dis_code: str, uf: str, anos: list) -> pd.DataFrame:
    print(f"[LOG] Carregando SINAN-{dis_code} para {uf}/{anos}...")
    sinan_db = SINAN().load()
    files = sinan_db.get_files(dis_code=dis_code, year=anos)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo SINAN-{dis_code} encontrado para {anos}.")
    downloaded = sinan_db.download(files)
    dfs = [p.to_dataframe() for p in downloaded if hasattr(p, 'to_dataframe')] if isinstance(downloaded, list) else [downloaded.to_dataframe()]
    if not dfs:
        raise ValueError("Falha ao converter os arquivos SINAN em DataFrames.")
    df = pd.concat(dfs, ignore_index=True)

    df_uf = df[df['SG_UF_NOT'].astype(str).isin([uf.upper(), {'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17', 'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27', 'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41', 'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53'}.get(uf.upper())])].copy()
    return df_uf


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    anos = args.anos if isinstance(args.anos, list) else [args.anos]

    print(f"\n--- [ETAPA 1] Carregando notificações de {args.dis_code} em {args.uf}/{anos} ---")
    df = carregar_notificacoes(args.dis_code, args.uf, anos)
    print(f"✅ {len(df)} notificações carregadas em {args.uf}.")

    dt_col = 'DT_NOTIFIC' if 'DT_NOTIFIC' in df.columns else 'DT_SIN_PRI'
    df[dt_col] = pd.to_datetime(df[dt_col], errors='coerce')
    df = df.dropna(subset=[dt_col, 'ID_MUNICIP'])
    df['MES'] = df[dt_col].dt.to_period('M').astype(str)
    df['CODMUN_6DIG'] = df['ID_MUNICIP'].astype(str).str[:6]

    print("\n--- [ETAPA 2] Agregando casos por município e mês ---")
    contagem = df.groupby(['CODMUN_6DIG', 'MES']).size().reset_index(name='CASOS')
    meses_disponiveis = sorted(contagem['MES'].unique())
    print(f"✅ {len(meses_disponiveis)} meses com dados, {contagem['CODMUN_6DIG'].nunique()} municípios afetados.")
    if len(meses_disponiveis) < 2:
        raise ValueError("Menos de 2 meses com notificações — não há progressão temporal para visualizar. Tente um período maior.")

    print("\n--- [ETAPA 3] Salvando série temporal dos municípios mais afetados ---")
    top_municipios = contagem.groupby('CODMUN_6DIG')['CASOS'].sum().sort_values(ascending=False).head(8).index.tolist()
    serie_larga = contagem[contagem['CODMUN_6DIG'].isin(top_municipios)].pivot(index='MES', columns='CODMUN_6DIG', values='CASOS').fillna(0).reset_index()
    serie_larga = serie_larga.rename(columns={'MES': 'periodo'})
    caminho_csv_serie = dir_saida / f"difusao_serie_temporal_{args.dis_code.lower()}_{args.uf.lower()}.csv"
    serie_larga.to_csv(caminho_csv_serie, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Série temporal (top {len(top_municipios)} municípios) salva em: '{caminho_csv_serie}'")

    print("\n--- [ETAPA 3b] Enriquecendo com coordenadas para o mapa animado ---")
    df_municipios = pd.read_csv(args.municipios_csv, dtype={'codigo_ibge': str})
    df_municipios['codigo_ibge'] = df_municipios['codigo_ibge'].str[:6]
    contagem_geo = contagem.merge(
        df_municipios[['codigo_ibge', 'nome', 'latitude', 'longitude']],
        left_on='CODMUN_6DIG', right_on='codigo_ibge', how='inner'
    ).rename(columns={'CODMUN_6DIG': 'cod_mun_ibge_6', 'nome': 'municipio', 'MES': 'periodo', 'CASOS': 'casos'})
    contagem_geo = contagem_geo[['cod_mun_ibge_6', 'municipio', 'latitude', 'longitude', 'periodo', 'casos']]
    caminho_csv_completo = dir_saida / f"difusao_casos_por_municipio_mes_{args.dis_code.lower()}_{args.uf.lower()}.csv"
    contagem_geo.to_csv(caminho_csv_completo, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Dados completos com coordenadas (todos os municípios/meses) salvos em: '{caminho_csv_completo}'")

    print("\n--- [ETAPA 4] Gerando grade de mapas (pequenos múltiplos) ---")
    gdf = carregar_geojson_uf(Path(args.geojson_dir), args.uf)
    meses_plotados = meses_disponiveis[:args.max_paineis]
    vmax = contagem['CASOS'].max()

    n_cols = min(3, len(meses_plotados))
    n_rows = (len(meses_plotados) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 6 * n_rows))
    axes_flat = axes.flatten() if hasattr(axes, 'flatten') else [axes]

    for i, mes in enumerate(meses_plotados):
        ax = axes_flat[i]
        contagem_mes = contagem[contagem['MES'] == mes][['CODMUN_6DIG', 'CASOS']]
        gdf_mes = gdf.merge(contagem_mes, on='CODMUN_6DIG', how='left')
        gdf_mes['CASOS'] = gdf_mes['CASOS'].fillna(0)
        gdf_mes.plot(ax=ax, column='CASOS', cmap='Reds', edgecolor='#999999', linewidth=0.3,
                     vmin=0, vmax=vmax, legend=(i == len(meses_plotados) - 1))
        ax.set_title(mes, fontsize=13)
        ax.set_axis_off()

    for j in range(len(meses_plotados), len(axes_flat)):
        axes_flat[j].set_axis_off()

    fig.suptitle(f"Difusão Espacial de {args.dis_code} em {args.uf} ({meses_plotados[0]} a {meses_plotados[-1]})", fontsize=16)
    plt.tight_layout()
    caminho_mapa = dir_saida / f"difusao_espacial_{args.dis_code.lower()}_{args.uf.lower()}.png"
    plt.savefig(caminho_mapa, dpi=180, bbox_inches='tight')
    plt.close()
    print(f"✅ Grade de mapas salva em: '{caminho_mapa}'")

    print("\n" + "=" * 80)
    print("🎉 DIFUSÃO ESPACIAL DE SURTO CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera pequenos múltiplos de mapas mostrando a difusão espacial mensal de um agravo do SINAN.")
    parser.add_argument("--dis-code", type=str, default="DENG", help="Código do agravo do SINAN (ex: DENG, CHIK, ZIKA).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados a considerar.")
    parser.add_argument("--max-paineis", dest="max_paineis", type=int, default=6, help="Número máximo de meses (painéis) a desenhar na grade.")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os GeoJSON de municípios.")
    parser.add_argument("--municipios_csv", type=str, default="referencia/espaciais/csv/municipios.csv", help="Caminho para o CSV com coordenadas dos municípios.")
    parser.add_argument("--dir_saida", type=str, default="outputs/difusao_espacial_surto", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
