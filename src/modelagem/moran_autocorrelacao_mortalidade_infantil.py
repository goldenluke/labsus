# -*- coding: utf-8 -*-
"""
======================================================================
  AUTOCORRELAÇÃO ESPACIAL (MORAN'S I) DA MORTALIDADE INFANTIL
======================================================================
Este script testa se a Taxa de Mortalidade Infantil (TMI) municipal está
distribuída aleatoriamente no espaço ou se forma clusters geográficos
(municípios com risco parecido perto uns dos outros). Usa o Índice de
Moran global, com significância avaliada por permutação (padrão da
literatura de epidemiologia espacial — ver "Fronteiras da Análise com
Dados do SINASC" no dicionário de dados do projeto).

Fonte: painel de indicadores (ex.: gerado por integrar_indicadores.py,
contendo a coluna TMI por cod_mun_ibge_6/UF/ANO) + GeoJSON de municípios.
"""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
from libpysal.weights import Queen
from esda.moran import Moran


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
    caminho = diretorio_geojson / nome_arquivo
    gdf = gpd.read_file(caminho)
    gdf['CODMUN_6DIG'] = gdf['id'].astype(str).str[:6]
    return gdf


def carregar_painel(caminho_csv: Path, uf: str, ano: int, indicador: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_csv, sep=';', dtype={'cod_mun_ibge_6': str})
    df = df[(df['UF'] == uf.upper()) & (df['ANO'] == ano)].copy()
    if indicador not in df.columns:
        raise KeyError(f"Indicador '{indicador}' não encontrado no painel. Colunas disponíveis: {list(df.columns)}")
    df = df[['cod_mun_ibge_6', indicador]].dropna()
    return df


def calcular_moran_global(gdf: gpd.GeoDataFrame, coluna_valor: str, permutacoes: int = 999) -> Moran:
    """Calcula o Índice de Moran global com pesos de contiguidade Queen."""
    w = Queen.from_dataframe(gdf, use_index=False)
    w.transform = 'r'
    moran = Moran(gdf[coluna_valor].values, w, permutations=permutacoes)
    return moran, w


def gerar_moran_scatterplot(gdf: gpd.GeoDataFrame, coluna_valor: str, w, moran: Moran, dir_saida: Path, indicador: str):
    import matplotlib.pyplot as plt
    import numpy as np

    y = gdf[coluna_valor].values
    y_z = (y - y.mean()) / y.std()
    y_lag_z = (w.sparse @ y_z)

    plt.figure(figsize=(8, 8))
    plt.scatter(y_z, y_lag_z, alpha=0.6, edgecolor='k')
    plt.axhline(0, color='grey', linestyle='--', linewidth=0.8)
    plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
    m, b = np.polyfit(y_z, y_lag_z, 1)
    xs = np.linspace(y_z.min(), y_z.max(), 50)
    plt.plot(xs, m * xs + b, color='red', linewidth=2)
    plt.title(f"Moran Scatterplot — {indicador}\nMoran's I = {moran.I:.4f} (p={moran.p_sim:.4f})")
    plt.xlabel(f"{indicador} (padronizado)")
    plt.ylabel(f"Média espacial dos vizinhos (padronizado)")
    caminho_fig = dir_saida / f"moran_scatterplot_{indicador.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Moran scatterplot salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando painel de indicadores para {args.uf}/{args.ano} ---")
    df_painel = carregar_painel(Path(args.painel_csv), args.uf, args.ano, args.indicador)
    print(f"✅ {len(df_painel)} municípios com dados válidos de '{args.indicador}'.")

    print(f"\n--- [ETAPA 2] Carregando geometria dos municípios de {args.uf} ---")
    gdf = carregar_geojson_uf(Path(args.geojson_dir), args.uf)

    gdf_merged = gdf.merge(df_painel, left_on='CODMUN_6DIG', right_on='cod_mun_ibge_6', how='inner')
    gdf_merged = gdf_merged.dropna(subset=[args.indicador]).reset_index(drop=True)
    print(f"✅ {len(gdf_merged)} municípios com geometria + indicador combinados.")

    if len(gdf_merged) < 5:
        print("❌ Poucos municípios para uma análise de autocorrelação espacial confiável (mínimo recomendado: 5).")
        return

    print(f"\n--- [ETAPA 3] Calculando Índice de Moran Global (permutações={args.permutacoes}) ---")
    moran, w = calcular_moran_global(gdf_merged, args.indicador, args.permutacoes)

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: AUTOCORRELAÇÃO ESPACIAL DE '{args.indicador}' EM {args.uf} ---")
    print("=" * 70)
    print(f"Índice de Moran (I): {moran.I:.4f}")
    print(f"Valor esperado sob aleatoriedade (E[I]): {moran.EI:.4f}")
    print(f"p-valor (teste de permutação, {args.permutacoes} permutações): {moran.p_sim:.4f}")
    if moran.p_sim < 0.05:
        direcao = "positiva (municípios parecidos tendem a ficar geograficamente próximos)" if moran.I > moran.EI else "negativa (padrão de tabuleiro de xadrez — vizinhos tendem a ser diferentes)"
        print(f"✅ Autocorrelação espacial estatisticamente significante e {direcao}.")
    else:
        print("⚠️ Não há evidência estatística de autocorrelação espacial (distribuição pode ser aleatória no espaço).")
    print("=" * 70)

    gerar_moran_scatterplot(gdf_merged, args.indicador, w, moran, dir_saida, args.indicador)

    resumo = pd.DataFrame([{
        'UF': args.uf, 'ANO': args.ano, 'INDICADOR': args.indicador,
        'MORAN_I': moran.I, 'MORAN_EI': moran.EI, 'P_VALOR_PERMUTACAO': moran.p_sim,
        'N_MUNICIPIOS': len(gdf_merged),
    }])
    caminho_csv = dir_saida / f"moran_global_{args.indicador.lower()}_{args.uf.lower()}_{args.ano}.csv"
    resumo.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resumo salvo em: '{caminho_csv}'")
    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE AUTOCORRELAÇÃO ESPACIAL CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula o Índice de Moran global para um indicador municipal.")
    parser.add_argument("--painel-csv", type=str, required=True, help="Caminho para o painel de indicadores (ex: gerado por integrar_indicadores.py).")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os arquivos GeoJSON de municípios.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar (ex: TO).")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência no painel.")
    parser.add_argument("--indicador", type=str, default="TMI", help="Nome da coluna de indicador a testar (padrão: TMI).")
    parser.add_argument("--permutacoes", type=int, default=999, help="Número de permutações para o teste de significância.")
    parser.add_argument("--dir_saida", type=str, default="outputs/moran_mortalidade_infantil", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
