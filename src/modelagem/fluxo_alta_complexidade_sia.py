# -*- coding: utf-8 -*-
"""
======================================================================
  MAPA DE FLUXO DE ALTA COMPLEXIDADE (SIA) — RESIDÊNCIA x ESTABELECIMENTO
======================================================================
Mesma lógica de `analise_fluxo_pacientes.py`, mas para procedimentos
AMBULATORIAIS de alta complexidade (SIA/PA) — ex.: quimioterapia,
radioterapia — em vez de internações (SIH). Compara o município de
RESIDÊNCIA do paciente (PA_MUNPCN) com o município do ESTABELECIMENTO
que realizou o procedimento (PA_UFMUN), filtrado por prefixos de
código de procedimento SIGTAP (PA_PROC_ID). Revela quais municípios
concentram a oferta desses serviços e de quão longe eles atraem pacientes.
"""

import argparse
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm

from pysus.online_data.SIA import download as download_sia


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_producao_sia(ufs: list, anos: list) -> pd.DataFrame:
    dfs = []
    for uf in ufs:
        for ano in anos:
            print(f"[LOG] Baixando SIA/PA para {uf}/{ano}...")
            downloaded = download_sia(states=uf, years=ano, months=list(range(1, 13)), groups=['PA'])
            arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
            if not arquivos:
                print(f"⚠️  Nenhum arquivo SIA/PA para {uf}/{ano}.")
                continue
            dfs.append(pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True))
    if not dfs:
        raise FileNotFoundError("Nenhum dado do SIA pôde ser carregado.")
    return pd.concat(dfs, ignore_index=True)


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    ufs = [u.upper() for u in (args.ufs if isinstance(args.ufs, list) else [args.ufs])]
    anos = args.anos if isinstance(args.anos, list) else [args.anos]
    proc_prefixos = args.proc_prefixos if isinstance(args.proc_prefixos, list) else [args.proc_prefixos]

    print(f"\n--- [ETAPA 1] Carregando produção ambulatorial (SIA/PA) para {ufs}/{anos} ---")
    df = carregar_producao_sia(ufs, anos)
    print(f"✅ {len(df)} registros de produção carregados.")

    print(f"\n--- [ETAPA 2] Filtrando procedimentos {proc_prefixos} e identificando rotas de fluxo ---")
    df['PA_PROC_ID'] = df['PA_PROC_ID'].astype(str)
    df_filtrado = df[df['PA_PROC_ID'].str.startswith(tuple(proc_prefixos))].copy()
    print(f"  -> {len(df_filtrado)} registros do(s) procedimento(s) selecionado(s).")

    df_fluxo = df_filtrado[['PA_MUNPCN', 'PA_UFMUN']].dropna()
    df_fluxo['PA_MUNPCN'] = df_fluxo['PA_MUNPCN'].astype(str).str[:6]
    df_fluxo['PA_UFMUN'] = df_fluxo['PA_UFMUN'].astype(str).str[:6]
    df_fluxo = df_fluxo[df_fluxo['PA_MUNPCN'] != df_fluxo['PA_UFMUN']]

    df_fluxo_agg = df_fluxo.groupby(['PA_MUNPCN', 'PA_UFMUN']).size().reset_index(name='N_PROCEDIMENTOS')
    df_fluxo_agg = df_fluxo_agg[df_fluxo_agg['N_PROCEDIMENTOS'] >= args.min_procedimentos_fluxo]
    print(f"✅ {len(df_fluxo_agg)} rotas de fluxo identificadas (mínimo {args.min_procedimentos_fluxo} procedimentos).")

    if df_fluxo_agg.empty:
        raise ValueError("Nenhuma rota de fluxo atingiu o mínimo definido. Tente reduzir --min-procedimentos-fluxo ou ajustar --proc-prefixos.")

    print("\n--- [ETAPA 3] Enriquecendo com coordenadas dos municípios ---")
    df_municipios = pd.read_csv(args.municipios_csv, dtype={'codigo_ibge': str})
    df_coords = df_municipios[['codigo_ibge', 'latitude', 'longitude', 'nome']].copy()
    df_coords['codigo_ibge'] = df_coords['codigo_ibge'].str[:6]

    df_final = pd.merge(df_fluxo_agg, df_coords, left_on='PA_MUNPCN', right_on='codigo_ibge', how='inner')
    df_final.rename(columns={'latitude': 'LAT_ORIGEM', 'longitude': 'LON_ORIGEM', 'nome': 'NOME_ORIGEM'}, inplace=True)
    df_final.drop('codigo_ibge', axis=1, inplace=True)
    df_final = pd.merge(df_final, df_coords, left_on='PA_UFMUN', right_on='codigo_ibge', how='inner')
    df_final.rename(columns={'latitude': 'LAT_DESTINO', 'longitude': 'LON_DESTINO', 'nome': 'NOME_DESTINO'}, inplace=True)
    df_final.drop('codigo_ibge', axis=1, inplace=True)

    caminho_csv = dir_saida / f"fluxo_alta_complexidade_{'_'.join(ufs).lower()}.csv"
    df_final.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Dados de fluxo salvos em: '{caminho_csv}'")

    print("\n--- [ETAPA 4] Gerando mapa de fluxo ---")
    gdf_brasil = gpd.read_file(args.shapefile)
    gdf_uf = gdf_brasil[gdf_brasil['SIGLA_UF'].isin(ufs)]

    fig, ax = plt.subplots(figsize=(15, 15))
    gdf_uf.plot(ax=ax, color='#e9e9e9', edgecolor='#666666', linewidth=0.7)

    norm = mcolors.LogNorm(vmin=df_final['N_PROCEDIMENTOS'].min(), vmax=df_final['N_PROCEDIMENTOS'].max())
    cmap = plt.cm.get_cmap('plasma')
    for _, row in df_final.iterrows():
        ax.plot([row['LON_ORIGEM'], row['LON_DESTINO']], [row['LAT_ORIGEM'], row['LAT_DESTINO']],
                color=cmap(norm(row['N_PROCEDIMENTOS'])),
                linewidth=1.0 + (norm(row['N_PROCEDIMENTOS']) * 5),
                solid_capstyle='round', alpha=0.7)

    ax.set_title(f"Fluxo de Alta Complexidade (proc. {', '.join(proc_prefixos)})\n({', '.join(ufs)} — {', '.join(map(str, anos))})", fontsize=18, pad=20)
    ax.set_axis_off()
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.5, aspect=20, label='Número de Procedimentos (Escala Log)')
    plt.tight_layout()

    caminho_mapa = dir_saida / f"mapa_fluxo_alta_complexidade_{'_'.join(ufs).lower()}.png"
    plt.savefig(caminho_mapa, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"✅ Mapa de fluxo salvo em: '{caminho_mapa}'")

    print("\n" + "=" * 80)
    print("🎉 MAPA DE FLUXO DE ALTA COMPLEXIDADE CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Gera um mapa de fluxo de procedimentos de alta complexidade (residência x estabelecimento) a partir do SIA.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos a processar.")
    parser.add_argument("--proc-prefixos", dest="proc_prefixos", nargs="+", default=["0304"], help="Prefixos de código de procedimento SIGTAP (ex: 0304 = quimioterapia, 0303 = radioterapia).")
    parser.add_argument("--min-procedimentos-fluxo", dest="min_procedimentos_fluxo", type=int, default=5, help="Número mínimo de procedimentos para desenhar uma rota de fluxo.")
    parser.add_argument("--municipios_csv", type=str, default=str(RAIZ_PROJETO / "referencia/espaciais/csv/municipios.csv"))
    parser.add_argument("--shapefile", type=str, default=str(RAIZ_PROJETO / "referencia/espaciais/shapefiles/municipios/BR_Municipios_2022/BR_Municipios_2022.shp"))
    parser.add_argument("--dir_saida", type=str, default=str(RAIZ_PROJETO / "outputs/fluxo_alta_complexidade"))
    args = parser.parse_args()
    main(args)
