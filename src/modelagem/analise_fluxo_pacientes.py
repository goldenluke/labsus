# -*- coding: utf-8 -*-
# Arquivo: src/features/analise_fluxo_pacientes.py

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import argparse
from pathlib import Path
from typing import List

from pysus.online_data.SIH import download as download_sih

def analisar_fluxo_pacientes(
    ufs: List[str],
    anos: List[int],
    diagnostico_cids: List[str],
    diagnostico_nome: str,
    caminho_municipios_csv: Path,
    shapefile_brasil: Path,
    dir_saida: Path,
    min_pacientes_fluxo: int = 5
):
    """
    Analisa o fluxo de pacientes entre municípios (residência vs. internação)
    para um diagnóstico específico e gera um mapa de fluxo.
    """
    print(f"\n--- Iniciando Análise de Fluxo de Pacientes para '{diagnostico_nome}' ---")

    # --- 1. Carregar Dados de Referência ---
    try:
        df_municipios = pd.read_csv(caminho_municipios_csv, dtype={'codigo_ibge': str})
        gdf_brasil = gpd.read_file(shapefile_brasil)
    except FileNotFoundError as e:
        print(f"❌ Erro crítico: Arquivo de referência não encontrado: {e}")
        return

    # --- 2. Coleta e Preparação dos Dados do SIH ---
    df_list = []
    for uf in ufs:
        for ano in anos:
            try:
                print(f"  -> Baixando dados do SIH para {uf}/{ano}...")
                downloaded_files = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
                if isinstance(downloaded_files, list):
                    df_sih = pd.concat([f.to_dataframe() for f in downloaded_files], ignore_index=True)
                else:
                    df_sih = downloaded_files.to_dataframe()
                df_list.append(df_sih)
            except Exception as e:
                print(f"⚠️ Erro ao baixar dados para {uf}/{ano}: {e}")

    if not df_list:
        print("❌ Nenhum dado do SIH pôde ser baixado. Análise abortada.")
        return

    df_total = pd.concat(df_list, ignore_index=True)
    print(f"Total de {len(df_total)} registos de internação baixados.")

    # --- 3. Filtrar e Processar os Fluxos ---
    df_diagnostico = df_total[df_total['DIAG_PRINC'].str.startswith(tuple(diagnostico_cids))].copy()
    print(f"  -> {len(df_diagnostico)} registos de '{diagnostico_nome}' encontrados.")

    df_fluxo = df_diagnostico[['MUNIC_RES', 'MUNIC_MOV']].dropna()
    df_fluxo['MUNIC_RES'] = df_fluxo['MUNIC_RES'].astype(str).str[:6]
    df_fluxo['MUNIC_MOV'] = df_fluxo['MUNIC_MOV'].astype(str).str[:6]
    df_fluxo = df_fluxo[df_fluxo['MUNIC_RES'] != df_fluxo['MUNIC_MOV']]

    df_fluxo_agg = df_fluxo.groupby(['MUNIC_RES', 'MUNIC_MOV']).size().reset_index(name='N_PACIENTES')
    df_fluxo_agg = df_fluxo_agg[df_fluxo_agg['N_PACIENTES'] >= min_pacientes_fluxo]
    print(f"  -> {len(df_fluxo_agg)} rotas de fluxo de pacientes identificadas (com no mínimo {min_pacientes_fluxo} pacientes).")

    if df_fluxo_agg.empty:
        print("⚠️ Nenhuma rota de fluxo significativa encontrada para plotar.")
        return

    # --- 4. Enriquecer com Coordenadas Geográficas ---
    df_coords = df_municipios[['codigo_ibge', 'latitude', 'longitude', 'nome']].copy()
    df_coords['codigo_ibge'] = df_coords['codigo_ibge'].str[:6]

    df_final = pd.merge(df_fluxo_agg, df_coords, left_on='MUNIC_RES', right_on='codigo_ibge', how='inner')
    df_final.rename(columns={'latitude': 'LAT_ORIGEM', 'longitude': 'LON_ORIGEM', 'nome': 'NOME_ORIGEM'}, inplace=True)
    df_final.drop('codigo_ibge', axis=1, inplace=True)

    df_final = pd.merge(df_final, df_coords, left_on='MUNIC_MOV', right_on='codigo_ibge', how='inner')
    df_final.rename(columns={'latitude': 'LAT_DESTINO', 'longitude': 'LON_DESTINO', 'nome': 'NOME_DESTINO'}, inplace=True)
    df_final.drop('codigo_ibge', axis=1, inplace=True)

    # --- 5. Salvar Resultados em CSV ---
    dir_saida.mkdir(parents=True, exist_ok=True)
    nome_arquivo_csv = f"fluxo_pacientes_{diagnostico_nome.lower().replace(' ', '_')}.csv"
    caminho_csv = dir_saida / nome_arquivo_csv
    df_final.to_csv(caminho_csv, index=False, sep=';')
    print(f"\n✅ Dados de fluxo salvos em: '{caminho_csv}'")

    # --- 6. Gerar Mapa de Fluxo (Versão Aprimorada) ---
    gdf_uf = gdf_brasil[gdf_brasil['SIGLA_UF'].isin(ufs)]

    fig, ax = plt.subplots(figsize=(15, 15))
    # ✅ ALTERAÇÃO: Divisões dos municípios mais evidentes
    gdf_uf.plot(ax=ax, color='#e9e9e9', edgecolor='#666666', linewidth=0.7)

    # Normaliza o número de pacientes para mapear para cores e espessuras
    norm = mcolors.LogNorm(vmin=df_final['N_PACIENTES'].min(), vmax=df_final['N_PACIENTES'].max())
    cmap = plt.cm.get_cmap('plasma')

    # Desenha as linhas de fluxo
    for _, row in df_final.iterrows():
        num_pacientes = row['N_PACIENTES']
        # ✅ ALTERAÇÃO: Linhas de fluxo mais grossas
        ax.plot([row['LON_ORIGEM'], row['LON_DESTINO']], [row['LAT_ORIGEM'], row['LAT_DESTINO']],
                color=cmap(norm(num_pacientes)),
                linewidth=1.0 + (norm(num_pacientes) * 5), # Aumentado de 0.8 + (...) * 4
                solid_capstyle='round',
                alpha=0.7)

    ax.set_title(f"Fluxo de Pacientes para Tratamento de {diagnostico_nome}\n({', '.join(ufs)} - {', '.join(map(str, anos))})", fontsize=18, pad=20)
    ax.set_axis_off()

    # Adiciona a barra de cores como legenda
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.5, aspect=20, label='Número de Pacientes (Escala Log)')

    plt.tight_layout()

    nome_arquivo_mapa = f"mapa_fluxo_{diagnostico_nome.lower().replace(' ', '_')}.png"
    caminho_mapa = dir_saida / nome_arquivo_mapa
    plt.savefig(caminho_mapa, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Mapa de fluxo aprimorado salvo em: '{caminho_mapa}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera uma análise de fluxo de pacientes para um diagnóstico específico.")

    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos a processar.")

    parser.add_argument("--cids", nargs="+", default=['C'], help="Lista de prefixos de CID-10 para filtrar o diagnóstico (ex: C para todas as neoplasias).")
    parser.add_argument("--nome", type=str, default="Neoplasias", help="Nome do diagnóstico para usar nos títulos e nomes de arquivos.")

    parser.add_argument("--municipios_csv", type=str, default=str(RAIZ_PROJETO / "referencia/espaciais/csv/municipios.csv"), help="Caminho para o CSV com coordenadas dos municípios.")
    parser.add_argument("--shapefile", type=str, default=str(RAIZ_PROJETO / "referencia/espaciais/shapefiles/municipios/BR_Municipios_2022/BR_Municipios_2022.shp"), help="Caminho para o shapefile do Brasil.")

    parser.add_argument("--dir_saida", type=str, default=str(RAIZ_PROJETO / "outputs/analises_fluxo"), help="Diretório de saída para os resultados.")
    parser.add_argument("--min_pacientes", type=int, default=5, help="Número mínimo de pacientes para desenhar uma rota de fluxo.")

    args = parser.parse_args()

    analisar_fluxo_pacientes(
        ufs=args.ufs,
        anos=args.anos,
        diagnostico_cids=args.cids,
        diagnostico_nome=args.nome,
        caminho_municipios_csv=Path(args.municipios_csv),
        shapefile_brasil=Path(args.shapefile),
        dir_saida=Path(args.dir_saida),
        min_pacientes_fluxo=args.min_pacientes
    )
