# -*- coding: utf-8 -*-
"""
======================================================================
  MORAN BIVARIADO: VULNERABILIDADE SOCIAL (IVS) x MORTALIDADE INFANTIL
======================================================================
Este script testa se a vulnerabilidade social de um município (IVS do
IPEA) está espacialmente associada à taxa de mortalidade infantil dos
municípios VIZINHOS — ou seja, se áreas de alta vulnerabilidade estão
cercadas por áreas de pior desfecho de saúde (e vice-versa). É o Índice
de Moran Bivariado, que estende a autocorrelação espacial simples para
medir a relação espacial ENTRE DUAS variáveis diferentes.

Fontes: painel geográfico com IVS (gerado por gerar_painel_geografico.py
ou analise_risco_geografico.py) + painel de indicadores com TMI.
"""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
from libpysal.weights import Queen
from esda.moran import Moran_BV


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


def carregar_ivs_e_tmi(caminho_geo_csv: Path, caminho_indicadores_csv: Path, uf: str, ano: int) -> pd.DataFrame:
    """Junta o IVS (painel geográfico) com a TMI (painel de indicadores) por município."""
    df_geo = pd.read_csv(caminho_geo_csv, sep=';', dtype={'CODMUNRES': str}, low_memory=False)
    colunas_geo_faltando = {'CODMUNRES', 'ivs'} - set(df_geo.columns)
    if colunas_geo_faltando:
        raise ValueError(
            f"O 'Painel Geográfico com IVS' selecionado não tem a(s) coluna(s) {sorted(colunas_geo_faltando)}. "
            "Gere um painel com o módulo 'Gerar Painel Geográfico (IVS + CNES)' e selecione o CSV produzido por ele."
        )
    df_geo_slim = df_geo[['CODMUNRES', 'ivs']].dropna().drop_duplicates(subset=['CODMUNRES'])
    df_geo_slim = df_geo_slim.rename(columns={'CODMUNRES': 'cod_mun_ibge_6', 'ivs': 'IVS'})

    df_ind = pd.read_csv(caminho_indicadores_csv, sep=';', dtype={'cod_mun_ibge_6': str})
    colunas_ind_faltando = {'cod_mun_ibge_6', 'UF', 'ANO', 'TMI'} - set(df_ind.columns)
    if colunas_ind_faltando:
        raise ValueError(
            f"O 'Painel de Indicadores' selecionado não tem a(s) coluna(s) {sorted(colunas_ind_faltando)}. "
            "Gere um painel na 'Integração de Indicadores' incluindo a Taxa de Mortalidade Infantil (TMI) "
            "entre os indicadores selecionados, e selecione esse CSV aqui."
        )
    df_ind = df_ind[(df_ind['UF'] == uf.upper()) & (df_ind['ANO'] == ano)][['cod_mun_ibge_6', 'TMI']].dropna()
    if df_ind.empty:
        raise ValueError(
            f"O 'Painel de Indicadores' selecionado não tem nenhuma linha para UF='{uf.upper()}' e ANO={ano}. "
            "Confira se o painel foi gerado para essa UF/ano, ou ajuste os parâmetros UF/Ano desta análise."
        )

    df_combinado = pd.merge(df_geo_slim, df_ind, on='cod_mun_ibge_6', how='inner')
    return df_combinado


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando IVS e TMI para {args.uf}/{args.ano} ---")
    df_combinado = carregar_ivs_e_tmi(Path(args.geo_csv), Path(args.indicadores_csv), args.uf, args.ano)
    print(f"✅ {len(df_combinado)} municípios com IVS e TMI disponíveis.")

    print(f"\n--- [ETAPA 2] Carregando geometria dos municípios de {args.uf} ---")
    gdf = carregar_geojson_uf(Path(args.geojson_dir), args.uf)
    gdf_merged = gdf.merge(df_combinado, left_on='CODMUN_6DIG', right_on='cod_mun_ibge_6', how='inner')
    gdf_merged = gdf_merged.dropna(subset=['IVS', 'TMI']).reset_index(drop=True)

    if len(gdf_merged) < 5:
        print("❌ Poucos municípios para uma análise de Moran bivariado confiável (mínimo recomendado: 5).")
        return

    print(f"\n--- [ETAPA 3] Calculando Moran Bivariado (IVS → vizinhança da TMI) ---")
    w = Queen.from_dataframe(gdf_merged, use_index=False)
    w.transform = 'r'
    moran_bv = Moran_BV(gdf_merged['IVS'].values, gdf_merged['TMI'].values, w, permutations=args.permutacoes)

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: MORAN BIVARIADO IVS x TMI EM {args.uf} ---")
    print("=" * 70)
    print(f"Índice de Moran Bivariado (I_biv): {moran_bv.I:.4f}")
    print(f"p-valor (permutação, {args.permutacoes} permutações): {moran_bv.p_sim:.4f}")
    correlacao_simples = gdf_merged['IVS'].corr(gdf_merged['TMI'])
    print(f"(Correlação de Pearson simples IVS x TMI, sem componente espacial, para referência: {correlacao_simples:.4f})")
    if moran_bv.p_sim < 0.05 and moran_bv.I > 0:
        print("✅ Há associação espacial positiva: municípios com IVS alto tendem a estar cercados por municípios com TMI alta.")
    elif moran_bv.p_sim < 0.05 and moran_bv.I < 0:
        print("✅ Há associação espacial negativa: municípios com IVS alto tendem a estar cercados por municípios com TMI baixa (padrão inesperado — investigar).")
    else:
        print("⚠️ Não há evidência estatística de associação espacial entre IVS e TMI (pode existir apenas em nível local, não municipal).")
    print("=" * 70)

    resumo = pd.DataFrame([{
        'UF': args.uf, 'ANO': args.ano, 'MORAN_BV_I': moran_bv.I, 'P_VALOR_PERMUTACAO': moran_bv.p_sim,
        'CORRELACAO_PEARSON_SIMPLES': correlacao_simples, 'N_MUNICIPIOS': len(gdf_merged),
    }])
    caminho_csv = dir_saida / f"moran_bivariado_ivs_tmi_{args.uf.lower()}_{args.ano}.csv"
    resumo.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resumo salvo em: '{caminho_csv}'")
    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE MORAN BIVARIADO CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula o Índice de Moran Bivariado entre IVS e Taxa de Mortalidade Infantil.")
    parser.add_argument("--geo-csv", type=str, required=True, help="Caminho para o painel geográfico com a coluna 'ivs' (gerado por gerar_painel_geografico.py ou analise_risco_geografico.py).")
    parser.add_argument("--indicadores-csv", type=str, required=True, help="Caminho para o painel de indicadores com a coluna 'TMI'.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência no painel de indicadores.")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os GeoJSON de municípios.")
    parser.add_argument("--permutacoes", type=int, default=999, help="Número de permutações do teste de significância.")
    parser.add_argument("--dir_saida", type=str, default="outputs/moran_bivariado_ivs_tmi", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
