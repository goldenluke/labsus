# -*- coding: utf-8 -*-
"""
======================================================================
  MAPA DE DESERTOS ASSISTENCIAIS (CNES) — DISTÂNCIA AO RECURSO MAIS PRÓXIMO
======================================================================
Para um tipo de estabelecimento escolhido (TP_UNID do CNES — ex.: 05 =
Hospital Geral, 07 = Hospital Especializado), identifica quais
municípios da UF possuem pelo menos um estabelecimento desse tipo e
calcula, para TODOS os municípios (inclusive os que já têm o recurso,
com distância zero), a distância em linha reta (haversine) até o
município mais próximo que o possui. Municípios "desertos" — longe de
qualquer unidade do tipo escolhido — aparecem destacados no mapa.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from pysus.online_data.CNES import download as download_cnes

MAPA_GEOJSON_UF = {
    'AC': 'geojs-12-mun.json', 'AL': 'geojs-27-mun.json', 'AM': 'geojs-13-mun.json', 'AP': 'geojs-16-mun.json',
    'BA': 'geojs-29-mun.json', 'CE': 'geojs-23-mun.json', 'DF': 'geojs-53-mun.json', 'ES': 'geojs-32-mun.json',
    'GO': 'geojs-52-mun.json', 'MA': 'geojs-21-mun.json', 'MG': 'geojs-31-mun.json', 'MS': 'geojs-50-mun.json',
    'MT': 'geojs-51-mun.json', 'PA': 'geojs-15-mun.json', 'PB': 'geojs-25-mun.json', 'PE': 'geojs-26-mun.json',
    'PI': 'geojs-22-mun.json', 'PR': 'geojs-41-mun.json', 'RJ': 'geojs-33-mun.json', 'RN': 'geojs-24-mun.json',
    'RO': 'geojs-11-mun.json', 'RR': 'geojs-14-mun.json', 'RS': 'geojs-43-mun.json', 'SC': 'geojs-42-mun.json',
    'SE': 'geojs-28-mun.json', 'SP': 'geojs-35-mun.json', 'TO': 'geojs-17-mun.json',
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Distância em km entre duas coordenadas geográficas."""
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_estabelecimentos(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando CNES (estabelecimentos) para {uf}/{ano}...")
    downloaded = download_cnes(group='ST', states=uf, years=ano, months=12)
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo CNES/ST encontrado para {uf}/{ano}.")
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    uf = args.uf.upper()
    tipos_unidade = args.tipos_unidade if isinstance(args.tipos_unidade, list) else [args.tipos_unidade]

    print(f"\n--- [ETAPA 1] Carregando estabelecimentos (CNES) para {uf}/{args.ano} ---")
    df_cnes = carregar_estabelecimentos(uf, args.ano)
    print(f"✅ {len(df_cnes)} estabelecimentos carregados.")

    df_cnes['TP_UNID'] = df_cnes['TP_UNID'].astype(str).str.zfill(2)
    df_cnes['CODUFMUN'] = df_cnes['CODUFMUN'].astype(str).str[:6]
    municipios_com_recurso = set(df_cnes[df_cnes['TP_UNID'].isin(tipos_unidade)]['CODUFMUN'].unique())
    print(f"✅ {len(municipios_com_recurso)} municípios possuem ao menos um estabelecimento do(s) tipo(s) {tipos_unidade}.")

    if not municipios_com_recurso:
        raise ValueError(f"Nenhum município de {uf} possui estabelecimento do(s) tipo(s) {tipos_unidade}. Tente outro tipo de unidade.")

    print("\n--- [ETAPA 2] Calculando distância de cada município ao recurso mais próximo ---")
    df_municipios = pd.read_csv(args.municipios_csv, dtype={'codigo_ibge': str})
    df_municipios['codigo_ibge'] = df_municipios['codigo_ibge'].str[:6]
    df_municipios['codigo_uf'] = df_municipios['codigo_uf'].astype(str)
    mapa_uf_para_codigo = {'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17', 'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27', 'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41', 'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53'}
    df_uf = df_municipios[df_municipios['codigo_uf'] == mapa_uf_para_codigo.get(uf)].copy()
    if df_uf.empty:
        raise ValueError(f"Nenhum município encontrado para a UF '{uf}' no arquivo de referência.")

    df_com_recurso = df_uf[df_uf['codigo_ibge'].isin(municipios_com_recurso)]
    coords_recurso = df_com_recurso[['latitude', 'longitude']].values

    distancias, nomes_mais_proximos = [], []
    for _, row in df_uf.iterrows():
        if row['codigo_ibge'] in municipios_com_recurso:
            distancias.append(0.0)
            nomes_mais_proximos.append(row['nome'])
            continue
        dists = haversine_distance(row['latitude'], row['longitude'], coords_recurso[:, 0], coords_recurso[:, 1])
        idx_min = int(np.argmin(dists))
        distancias.append(float(dists[idx_min]))
        nomes_mais_proximos.append(df_com_recurso.iloc[idx_min]['nome'])

    df_uf['TEM_RECURSO'] = df_uf['codigo_ibge'].isin(municipios_com_recurso)
    df_uf['DISTANCIA_KM_RECURSO_MAIS_PROXIMO'] = distancias
    df_uf['MUNICIPIO_RECURSO_MAIS_PROXIMO'] = nomes_mais_proximos
    df_resultado = df_uf[['codigo_ibge', 'nome', 'latitude', 'longitude', 'TEM_RECURSO', 'DISTANCIA_KM_RECURSO_MAIS_PROXIMO', 'MUNICIPIO_RECURSO_MAIS_PROXIMO']].rename(columns={'codigo_ibge': 'cod_mun_ibge_6', 'nome': 'municipio'})
    df_resultado = df_resultado.sort_values('DISTANCIA_KM_RECURSO_MAIS_PROXIMO', ascending=False)

    caminho_csv = dir_saida / f"desertos_assistenciais_{uf.lower()}_{args.ano}.csv"
    df_resultado.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Distâncias calculadas para {len(df_resultado)} municípios, salvas em: '{caminho_csv}'")
    print(f"   Município mais isolado: {df_resultado.iloc[0]['municipio']} ({df_resultado.iloc[0]['DISTANCIA_KM_RECURSO_MAIS_PROXIMO']:.1f} km)")

    print("\n--- [ETAPA 3] Gerando mapa de desertos assistenciais ---")
    gdf = gpd.read_file(Path(args.geojson_dir) / MAPA_GEOJSON_UF[uf])
    gdf['CODMUN_6DIG'] = gdf['id'].astype(str).str[:6]
    gdf_mapa = gdf.merge(df_resultado, left_on='CODMUN_6DIG', right_on='cod_mun_ibge_6', how='inner')

    fig, ax = plt.subplots(figsize=(12, 12))
    gdf_mapa.plot(ax=ax, column='DISTANCIA_KM_RECURSO_MAIS_PROXIMO', cmap='OrRd', edgecolor='#666666',
                  linewidth=0.4, legend=True, legend_kwds={'label': 'Distância ao recurso mais próximo (km)', 'shrink': 0.6})
    ax.set_title(f"Desertos Assistenciais em {uf} — Tipo(s) de Unidade {tipos_unidade} ({args.ano})", fontsize=15, pad=15)
    ax.set_axis_off()
    plt.tight_layout()
    caminho_mapa = dir_saida / f"mapa_desertos_assistenciais_{uf.lower()}_{args.ano}.png"
    plt.savefig(caminho_mapa, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"✅ Mapa salvo em: '{caminho_mapa}'")

    print("\n" + "=" * 80)
    print("🎉 MAPA DE DESERTOS ASSISTENCIAIS CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mapeia a distância de cada município ao estabelecimento de saúde de um tipo específico mais próximo (CNES).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência (competência CNES).")
    parser.add_argument("--tipos-unidade", dest="tipos_unidade", nargs="+", default=["05", "07"], help="Códigos TP_UNID do CNES a considerar como 'recurso' (ex: 05=Hospital Geral, 07=Hospital Especializado, 02=UBS).")
    parser.add_argument("--municipios_csv", type=str, default="referencia/espaciais/csv/municipios.csv")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os GeoJSON de municípios.")
    parser.add_argument("--dir_saida", type=str, default="outputs/desertos_assistenciais", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
