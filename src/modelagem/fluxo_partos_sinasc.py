# -*- coding: utf-8 -*-
"""
======================================================================
  MAPA DE FLUXO DE PARTOS (SINASC) — RESIDÊNCIA x OCORRÊNCIA
======================================================================
Mesma lógica de `analise_fluxo_pacientes.py` (SIH: residência x
internação), aplicada ao SINASC: compara o município de RESIDÊNCIA da
mãe (CODMUNRES) com o município de OCORRÊNCIA do parto (CODMUNNASC) e
desenha um mapa de fluxo — as linhas revelam quais municípios "exportam"
gestantes para dar à luz em outro lugar (tipicamente por falta de
maternidade/UTI neonatal local) e quais municípios funcionam como polos
de referência obstétrica.
"""

import argparse
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm

from pysus.online_data.SINASC import download as download_sinasc


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_partos(ufs: list, anos: list) -> pd.DataFrame:
    dfs = []
    for uf in ufs:
        for ano in anos:
            print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
            downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
            arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
            if not arquivos:
                print(f"⚠️  Nenhum arquivo SINASC para {uf}/{ano}.")
                continue
            dfs.append(pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True))
    if not dfs:
        raise FileNotFoundError("Nenhum dado do SINASC pôde ser carregado.")
    return pd.concat(dfs, ignore_index=True)


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    ufs = [u.upper() for u in (args.ufs if isinstance(args.ufs, list) else [args.ufs])]
    anos = args.anos if isinstance(args.anos, list) else [args.anos]

    print(f"\n--- [ETAPA 1] Carregando nascimentos (SINASC) para {ufs}/{anos} ---")
    df = carregar_partos(ufs, anos)
    print(f"✅ {len(df)} nascimentos carregados.")

    print("\n--- [ETAPA 2] Identificando rotas de fluxo (residência ≠ ocorrência) ---")
    df_fluxo = df[['CODMUNRES', 'CODMUNNASC']].dropna()
    df_fluxo['CODMUNRES'] = df_fluxo['CODMUNRES'].astype(str).str[:6]
    df_fluxo['CODMUNNASC'] = df_fluxo['CODMUNNASC'].astype(str).str[:6]
    df_fluxo = df_fluxo[df_fluxo['CODMUNRES'] != df_fluxo['CODMUNNASC']]

    df_fluxo_agg = df_fluxo.groupby(['CODMUNRES', 'CODMUNNASC']).size().reset_index(name='N_PARTOS')
    df_fluxo_agg = df_fluxo_agg[df_fluxo_agg['N_PARTOS'] >= args.min_partos_fluxo]
    print(f"✅ {len(df_fluxo_agg)} rotas de fluxo identificadas (mínimo {args.min_partos_fluxo} partos).")

    if df_fluxo_agg.empty:
        raise ValueError("Nenhuma rota de fluxo de partos atingiu o mínimo definido. Tente reduzir --min-partos-fluxo.")

    print("\n--- [ETAPA 3] Enriquecendo com coordenadas dos municípios ---")
    df_municipios = pd.read_csv(args.municipios_csv, dtype={'codigo_ibge': str})
    df_coords = df_municipios[['codigo_ibge', 'latitude', 'longitude', 'nome']].copy()
    df_coords['codigo_ibge'] = df_coords['codigo_ibge'].str[:6]

    df_final = pd.merge(df_fluxo_agg, df_coords, left_on='CODMUNRES', right_on='codigo_ibge', how='inner')
    df_final.rename(columns={'latitude': 'LAT_ORIGEM', 'longitude': 'LON_ORIGEM', 'nome': 'NOME_ORIGEM'}, inplace=True)
    df_final.drop('codigo_ibge', axis=1, inplace=True)
    df_final = pd.merge(df_final, df_coords, left_on='CODMUNNASC', right_on='codigo_ibge', how='inner')
    df_final.rename(columns={'latitude': 'LAT_DESTINO', 'longitude': 'LON_DESTINO', 'nome': 'NOME_DESTINO'}, inplace=True)
    df_final.drop('codigo_ibge', axis=1, inplace=True)

    caminho_csv = dir_saida / f"fluxo_partos_{'_'.join(ufs).lower()}.csv"
    df_final.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Dados de fluxo salvos em: '{caminho_csv}'")

    print("\n--- [ETAPA 4] Gerando mapa de fluxo ---")
    gdf_brasil = gpd.read_file(args.shapefile)
    gdf_uf = gdf_brasil[gdf_brasil['SIGLA_UF'].isin(ufs)]

    fig, ax = plt.subplots(figsize=(15, 15))
    gdf_uf.plot(ax=ax, color='#e9e9e9', edgecolor='#666666', linewidth=0.7)

    norm = mcolors.LogNorm(vmin=df_final['N_PARTOS'].min(), vmax=df_final['N_PARTOS'].max())
    cmap = plt.cm.get_cmap('plasma')
    for _, row in df_final.iterrows():
        ax.plot([row['LON_ORIGEM'], row['LON_DESTINO']], [row['LAT_ORIGEM'], row['LAT_DESTINO']],
                color=cmap(norm(row['N_PARTOS'])),
                linewidth=1.0 + (norm(row['N_PARTOS']) * 5),
                solid_capstyle='round', alpha=0.7)

    ax.set_title(f"Fluxo de Partos: Residência x Local de Ocorrência\n({', '.join(ufs)} — {', '.join(map(str, anos))})", fontsize=18, pad=20)
    ax.set_axis_off()
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.5, aspect=20, label='Número de Partos (Escala Log)')
    plt.tight_layout()

    caminho_mapa = dir_saida / f"mapa_fluxo_partos_{'_'.join(ufs).lower()}.png"
    plt.savefig(caminho_mapa, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"✅ Mapa de fluxo salvo em: '{caminho_mapa}'")

    print("\n" + "=" * 80)
    print("🎉 MAPA DE FLUXO DE PARTOS CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Gera um mapa de fluxo de partos (residência x ocorrência) a partir do SINASC.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos a processar.")
    parser.add_argument("--min-partos-fluxo", dest="min_partos_fluxo", type=int, default=5, help="Número mínimo de partos para desenhar uma rota de fluxo.")
    parser.add_argument("--municipios_csv", type=str, default=str(RAIZ_PROJETO / "referencia/espaciais/csv/municipios.csv"))
    parser.add_argument("--shapefile", type=str, default=str(RAIZ_PROJETO / "referencia/espaciais/shapefiles/municipios/BR_Municipios_2022/BR_Municipios_2022.shp"))
    parser.add_argument("--dir_saida", type=str, default=str(RAIZ_PROJETO / "outputs/fluxo_partos"))
    args = parser.parse_args()
    main(args)
