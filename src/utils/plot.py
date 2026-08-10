# Arquivo: utils/plot.py
# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

def charts(
    df, uf: str, ano: int, coluna_valor: str,
    legenda: str, cmap: str, nome_arquivo: str,
    output_dir: str = "outputs/charts",
    title: str = None,
    ativo=False):
    if not ativo:
        print("Geração de mapa desativada.")
        return
    """
    Gera e salva um mapa temático para o indicador desejado.

    Parâmetros:
    - df: DataFrame com os valores do indicador indexado por código de município (6 dígitos).
    - uf (str): Sigla da UF (ex: 'TO').
    - ano (int): Ano de referência.
    - coluna_valor (str): Nome da coluna com os valores a serem mapeados.
    - legenda (str): Legenda da barra de cores.
    - cmap (str): Colormap para o indicador (ex: 'Greens', 'Blues').
    - nome_arquivo (str): Nome base do arquivo a ser salvo.
    - output_dir (str): Diretório de saída.
    - title (str): Título do mapa (opcional). Se não fornecido, será gerado automaticamente.
    """
    try:
        # 1: carregar shapefile
        shp = "shapefiles/BR_Municipios_2022.shp"
        gdf = gpd.read_file(shp)
        gdf = gdf[gdf["SIGLA_UF"] == uf].copy()
        gdf["CD_MUN"] = gdf["CD_MUN"].astype(str).str[:6]

        # 2: juntar com dados
        gdf = (
            gdf.set_index("CD_MUN")
               .join(df[[coluna_valor]], how="left")
               .fillna({coluna_valor: 0})
        )

        # 3: criar mapa
        fig, ax = plt.subplots(figsize=(12, 10))
        gdf.plot(
            column=coluna_valor,
            cmap=cmap,
            linewidth=0.5,
            edgecolor="black",
            legend=True,
            legend_kwds={'label': legenda},
            ax=ax
        )

        # 4: título e layout
        if not title:
            title = f"{uf} – {legenda} ({ano})"
        ax.set_title(title, fontsize=14)
        ax.axis("off")
        plt.tight_layout()

        # 5: salvar arquivo
        os.makedirs(output_dir, exist_ok=True)
        fn = f"{output_dir}/mapa_{nome_arquivo}_{uf.lower()}_{ano}.png"
        plt.savefig(fn, dpi=300)
        plt.close(fig)
        print(f"🗺️ Mapa salvo: {fn}")

    except Exception as e:
        print(f"❌ Erro ao gerar mapa {uf}/{ano}: {e}")


def gerar_mapa_perfis(
    df_analise: pd.DataFrame,
    uf_sigla: str, ano: int,
    cores_perfis: dict,
    output_path: str,
    shapefile_path: str = "shapefiles/BR_Municipios_2022.shp"
):
    """Gera e salva um mapa temático CATEGÓRICO para os perfis de saúde."""
    print(f"🗺️  Gerando mapa de perfis para {uf_sigla}/{ano}...")
    try:
        gdf_mun = gpd.read_file(shapefile_path)
        gdf_uf = gdf_mun[gdf_mun["SIGLA_UF"] == uf_sigla].copy()
        gdf_uf["CD_MUN"] = gdf_uf["CD_MUN"].astype(str).str[:6]

        df_mapa = df_analise[['cod_mun_ibge_6', 'cor', 'perfil']].copy()
        df_mapa['cod_mun_ibge_6'] = df_mapa['cod_mun_ibge_6'].astype(str)

        gdf_final = gdf_uf.merge(df_mapa, left_on='CD_MUN', right_on='cod_mun_ibge_6')

        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        gdf_final.plot(color=gdf_final['cor'], linewidth=0.5, edgecolor="black", ax=ax)

        perfis_presentes = sorted([p for p in gdf_final['perfil'].unique() if p in cores_perfis])
        patches = [mpatches.Patch(color=cores_perfis[label], label=label) for label in perfis_presentes]
        ax.legend(handles=patches, title="Perfis de Saúde", loc='upper right', fontsize=12, title_fontsize=14)

        ax.set_title(f'Mapa de Perfis de Saúde - {uf_sigla} - {ano}', loc='left', fontsize=18, fontweight='bold')
        ax.axis("off")
        plt.tight_layout()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Mapa de Perfis salvo em: {output_path}")
    except Exception as e:
        print(f"❌ Erro ao gerar mapa de perfis para {uf_sigla}/{ano}: {e}")
