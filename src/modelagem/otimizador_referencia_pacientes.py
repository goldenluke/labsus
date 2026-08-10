# -*- coding: utf-8 -*-
"""
======================================================================
  OTIMIZADOR DE REFERÊNCIA DE PACIENTES DE ALTO RISCO
======================================================================
Este script implementa um pipeline de simulação para apoiar a decisão
de referência de pacientes, utilizando dados geográficos de arquivos GeoJSON.
"""

import pandas as pd
from pathlib import Path
import argparse
import joblib
import numpy as np
import geopandas as gpd

try:
    from src.modelagem.analise_sobrevida_infantil import preparar_dados_para_modelo
except ImportError:
    preparar_dados_para_modelo = None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula a distância em km entre duas coordenadas geográficas."""
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def carregar_artefatos(caminho_modelo_sobrevida: Path, diretorio_geojson: Path, ufs: list):
    """Carrega o modelo treinado e os dados de coordenadas e nomes dos arquivos GeoJSON."""
    print("\n--- [ETAPA 1] Carregando modelo e dados de referência ---")
    try:
        modelo = joblib.load(caminho_modelo_sobrevida)
        print(f"✅ Modelo de sobrevida '{caminho_modelo_sobrevida.name}' carregado.")
    except FileNotFoundError:
        print(f"❌ ERRO: Modelo não encontrado em '{caminho_modelo_sobrevida}'."); return None, None
    mapa_arquivos_geojson = {'AC': 'geojs-12-mun.json', 'AL': 'geojs-27-mun.json', 'AM': 'geojs-13-mun.json', 'AP': 'geojs-16-mun.json', 'BA': 'geojs-29-mun.json', 'CE': 'geojs-23-mun.json', 'DF': 'geojs-53-mun.json', 'ES': 'geojs-32-mun.json', 'GO': 'geojs-52-mun.json', 'MA': 'geojs-21-mun.json', 'MG': 'geojs-31-mun.json', 'MS': 'geojs-50-mun.json', 'MT': 'geojs-51-mun.json', 'PA': 'geojs-15-mun.json', 'PB': 'geojs-25-mun.json', 'PE': 'geojs-26-mun.json', 'PI': 'geojs-22-mun.json', 'PR': 'geojs-41-mun.json', 'RJ': 'geojs-33-mun.json', 'RN': 'geojs-24-mun.json', 'RO': 'geojs-11-mun.json', 'RR': 'geojs-14-mun.json', 'RS': 'geojs-43-mun.json', 'SC': 'geojs-42-mun.json', 'SE': 'geojs-28-mun.json', 'SP': 'geojs-35-mun.json', 'TO': 'geojs-17-mun.json'}
    gdfs = []
    for uf in ufs:
        nome_arquivo = mapa_arquivos_geojson.get(uf.upper())
        if nome_arquivo: gdfs.append(gpd.read_file(diretorio_geojson / nome_arquivo))
    if not gdfs: print("❌ ERRO: Nenhum dado geográfico pôde ser carregado."); return None, None
    gdf_completo = pd.concat(gdfs, ignore_index=True)
    gdf_completo['centroide'] = gdf_completo['geometry'].centroid
    gdf_completo['longitude'] = gdf_completo.centroide.x; gdf_completo['latitude'] = gdf_completo.centroide.y
    df_geo = pd.DataFrame(gdf_completo[['id', 'name', 'latitude', 'longitude']]).rename(columns={'id': 'CODMUN_6DIG', 'name': 'NOME_MUNICIPIO'})
    df_geo['CODMUN_6DIG'] = df_geo['CODMUN_6DIG'].astype(str).str[:6]
    print(f"✅ Dados geográficos de {len(df_geo)} municípios extraídos.")
    return modelo, df_geo

def otimizar_referencia(modelo_sobrevida, df_geo: pd.DataFrame, df_coorte: pd.DataFrame, df_hospitais_destino: pd.DataFrame):
    """Simula os desfechos e calcula o score de otimização."""
    print("\n--- [ETAPA 2] Executando simulação de referência ---")
    resultados_simulacao = []
    if preparar_dados_para_modelo is None: return pd.DataFrame()
    X_coorte, _ = preparar_dados_para_modelo(df_coorte)
    cod_origem = df_coorte['CODMUNRES_6DIG'].iloc[0]
    coords_origem = df_geo[df_geo['CODMUN_6DIG'] == cod_origem]
    if coords_origem.empty:
        print(f"❌ ERRO: Coordenadas não encontradas para o município de origem {cod_origem}."); return pd.DataFrame()
    lat_origem, lon_origem = coords_origem.iloc[0]['latitude'], coords_origem.iloc[0]['longitude']
    for paciente_idx, paciente_row in X_coorte.iterrows():
        for hospital_idx, hospital_row in df_hospitais_destino.iterrows():
            cenario = paciente_row.copy(); cenario['QTLEIT39'] = hospital_row['QTLEIT39']; cenario['ATIVIDAD'] = hospital_row['ATIVIDAD']
            prob_obito = modelo_sobrevida.predict_proba(pd.DataFrame([cenario]))[0, 1]
            resultados_simulacao.append({
                'MUNICIPIO_ORIGEM_COD': cod_origem, 'HOSPITAL_DESTINO_CNES': hospital_row['CNES'], 'MUNICIPIO_DESTINO_COD': hospital_row['CODMUNNASC_6DIG'],
                'PROB_SOBREVIDA': 1 - prob_obito, 'CUSTO_ESTIMADO': hospital_row.get('CUSTO_MEDIO_NEONATAL', 5000),
                'DISTANCIA_KM': haversine_distance(lat_origem, lon_origem, hospital_row['latitude'], hospital_row['longitude'])
            })
    df_resultados = pd.DataFrame(resultados_simulacao)
    print("\n--- [ETAPA 3] Calculando Score de Otimização ---")
    def normalizar(coluna):
        min_val, max_val = coluna.min(), coluna.max()
        if max_val == min_val: return 1.0
        return (coluna - min_val) / (max_val - min_val)
    df_resultados['SCORE_SOBREVIDA'] = normalizar(df_resultados['PROB_SOBREVIDA'])
    df_resultados['SCORE_CUSTO'] = 1 - normalizar(df_resultados['CUSTO_ESTIMADO'])
    df_resultados['SCORE_DISTANCIA'] = 1 - normalizar(df_resultados['DISTANCIA_KM'])
    peso_vida = 0.6; peso_custo = 0.2; peso_distancia = 0.2
    df_resultados['SCORE_FINAL'] = (peso_vida * df_resultados['SCORE_SOBREVIDA'] + peso_custo * df_resultados['SCORE_CUSTO'] + peso_distancia * df_resultados['SCORE_DISTANCIA'])
    print("✅ Simulação e scoring concluídos.")
    return df_resultados.sort_values('SCORE_FINAL', ascending=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simula e otimiza a referência de pacientes de alto risco.")
    parser.add_argument("--painel-base-csv", type=str, required=True, help="Caminho para o painel de sobrevida infantil.")
    parser.add_argument("--modelo-sobrevida", type=str, default="outputs/analise_sobrevida/modelo_sobrevida_infantil.joblib", help="Caminho para o modelo de sobrevida treinado.")
    parser.add_argument("--geojson-dir", type=str, default="referencia/espaciais/geojson/municipios", help="Diretório com os arquivos GeoJSON.")
    parser.add_argument("--municipio-origem", type=str, required=True, help="Código IBGE (6 dígitos) do município de origem.")
    parser.add_argument("--ufs-referencia", nargs="+", required=True, help="Lista de UFs onde os hospitais de destino serão procurados.")
    parser.add_argument("--dir_saida", type=str, default="outputs/otimizacao_referencia", help="Diretório para salvar o relatório.")
    args = parser.parse_args()
    modelo, df_geo = carregar_artefatos(Path(args.modelo_sobrevida), Path(args.geojson_dir), args.ufs_referencia)
    if modelo and df_geo is not None:
        df_base = pd.read_csv(Path(args.painel_base_csv), sep=';')
        df_base['CODMUNRES_6DIG'] = df_base['CODMUNRES'].astype(str).str[:6]
        coorte_pacientes = df_base[(df_base['CODMUNRES_6DIG'] == args.municipio_origem) & (pd.to_numeric(df_base['GESTACAO'], errors='coerce') < 5)].copy()
        hospitais_destino = df_base[pd.to_numeric(df_base['QTLEIT39'], errors='coerce') > 0].copy()
        if 'VINC_SUS' not in hospitais_destino.columns: hospitais_destino['VINC_SUS'] = 'N/A'
        hospitais_destino['VINC_SUS'] = hospitais_destino['VINC_SUS'].fillna('N/A').astype(str)
        hospitais_destino.drop_duplicates(subset=['CNES'], inplace=True)
        hospitais_destino['CODMUNNASC_6DIG'] = hospitais_destino['CODMUNNASC'].astype(str).str[:6]
        hospitais_destino = pd.merge(hospitais_destino, df_geo, left_on='CODMUNNASC_6DIG', right_on='CODMUN_6DIG', how='left').dropna(subset=['latitude', 'longitude'])
        if not coorte_pacientes.empty and not hospitais_destino.empty and preparar_dados_para_modelo:
            df_ranking = otimizar_referencia(modelo, df_geo, coorte_pacientes, hospitais_destino)
            if not df_ranking.empty:
                df_ranking = pd.merge(df_ranking, hospitais_destino[['CNES', 'VINC_SUS']], left_on='HOSPITAL_DESTINO_CNES', right_on='CNES', how='left')
                df_geo_nomes_origem = df_geo.rename(columns={'NOME_MUNICIPIO': 'NOME_MUNICIPIO_ORIGEM', 'CODMUN_6DIG': 'MUNICIPIO_ORIGEM_COD'})
                df_ranking = pd.merge(df_ranking, df_geo_nomes_origem[['MUNICIPIO_ORIGEM_COD', 'NOME_MUNICIPIO_ORIGEM']], on='MUNICIPIO_ORIGEM_COD', how='left')
                df_geo_nomes_destino = df_geo.rename(columns={'NOME_MUNICIPIO': 'NOME_MUNICIPIO_DESTINO', 'CODMUN_6DIG': 'MUNICIPIO_DESTINO_COD'})
                df_ranking = pd.merge(df_ranking, df_geo_nomes_destino[['MUNICIPIO_DESTINO_COD', 'NOME_MUNICIPIO_DESTINO']], on='MUNICIPIO_DESTINO_COD', how='left')

                colunas_agrupamento = ['MUNICIPIO_ORIGEM_COD', 'NOME_MUNICIPIO_ORIGEM', 'HOSPITAL_DESTINO_CNES', 'MUNICIPIO_DESTINO_COD', 'NOME_MUNICIPIO_DESTINO', 'VINC_SUS']
                colunas_numericas = ['PROB_SOBREVIDA', 'CUSTO_ESTIMADO', 'DISTANCIA_KM', 'SCORE_FINAL']

                ranking_final = df_ranking.groupby(colunas_agrupamento)[colunas_numericas].mean().sort_values('SCORE_FINAL', ascending=False)
                output_dir = Path(args.dir_saida)
                output_dir.mkdir(parents=True, exist_ok=True)
                nome_origem = ranking_final.index.get_level_values('NOME_MUNICIPIO_ORIGEM')[0]
                caminho_csv = output_dir / f"ranking_referencia_para_{nome_origem.replace(' ', '_')}_{args.municipio_origem}.csv"
                ranking_final.to_csv(caminho_csv, sep=';', encoding='utf-8-sig')
                print(f"\n📄 Relatório de otimização salvo em: '{caminho_csv}'")
                print("\n--- Top 15 Hospitais Recomendados ---"); print(ranking_final.head(15))
                print("\n" + "="*80); print("🎉 PIPELINE DE OTIMIZAÇÃO DE REFERÊNCIA CONCLUÍDO! 🎉"); print("="*80)
