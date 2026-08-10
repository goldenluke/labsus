# -*- coding: utf-8 -*-
"""
======================================================================
  PIPELINE DE DETECÇÃO DE SURTOS E ANOMALIAS EM SÉRIES TEMPORAIS
======================================================================
Este script implementa um sistema de alerta precoce para a detecção
de surtos de doenças infecciosas.
"""

import pandas as pd
from pathlib import Path
import argparse
import itertools

# Importações do PySUS
from pysus.online_data.SINAN import SINAN

# Ferramentas de Forecasting
from prophet import Prophet
import matplotlib.pyplot as plt


def carregar_dados_sinan_historico(ufs: list, anos: list, agravo: str):
    """Carrega múltiplos anos de dados do SINAN para um agravo específico."""
    print(f"\n--- [ETAPA 1] Carregando dados do SINAN-{agravo} para {ufs}/{anos} ---")

    try:
        sinan_db = SINAN().load()
        # O módulo SINAN não aceita filtro de UF, carregamos para o Brasil e filtramos depois.
        files = sinan_db.get_files(dis_code=agravo, year=anos)
        if not files:
            print(f"⚠️ Nenhum arquivo SINAN/{agravo} encontrado para os anos fornecidos.")
            return pd.DataFrame()

        print(f"[LOG] Baixando e processando {len(files)} arquivo(s)...")

        # ==========================================================
        # --- CORREÇÃO APLICADA AQUI ---
        # Lógica robusta para tratar o retorno da função de download
        # ==========================================================
        downloaded = sinan_db.download(files)

        if isinstance(downloaded, list):
            df_brasil = pd.concat([p.to_dataframe() for p in downloaded if hasattr(p, 'to_dataframe')], ignore_index=True)
        elif hasattr(downloaded, "to_dataframe"):
            df_brasil = downloaded.to_dataframe()
        else:
            df_brasil = pd.DataFrame()
        # ==========================================================

        if df_brasil.empty:
            print("❌ Nenhum dado pôde ser carregado.")
            return pd.DataFrame()

        # Filtro pós-carregamento pela UF de notificação
        ufs_codigos_ibge = [str(uf_map[uf.upper()]) for uf in ufs if uf.upper() in uf_map]
        df_filtrado = df_brasil[df_brasil['SG_UF_NOT'].isin(ufs_codigos_ibge)].copy()

        print(f"✅ Dados carregados e filtrados para {ufs}. Total de {len(df_filtrado)} notificações.")
        return df_filtrado

    except Exception as e:
        print(f"❌ Erro crítico durante o carregamento de dados: {e}")
        return pd.DataFrame()


def detectar_anomalias_por_municipio(df: pd.DataFrame, mapa_nomes_municipio: dict):
    """
    Itera sobre os municípios, treina um modelo Prophet para cada um e detecta anomalias.
    """
    print("\n--- [ETAPA 2] Analisando séries temporais e detectando anomalias ---")

    alertas_gerais = []

    # Mapeia o código do município para o nome para relatórios mais claros
    # (mapa_nomes_municipio já é {ID_MUNICIP: nome}, não precisa ser invertido)
    df['NOME_MUNICIPIO'] = df['ID_MUNICIP'].map(mapa_nomes_municipio)

    for municipio, df_mun in df.groupby('ID_MUNICIP'):
        nome_municipio = df_mun['NOME_MUNICIPIO'].iloc[0] if pd.notna(df_mun['NOME_MUNICIPIO'].iloc[0]) else municipio
        print(f"  -> Processando município: {nome_municipio} ({municipio})...")

        if len(df_mun) < 104: # Requer pelo menos 2 anos de dados para detectar sazonalidade
            print("     -> Dados insuficientes (menos de 2 anos). Pulando.")
            continue

        # 1. Criar a série temporal semanal
        df_mun['DT_NOTIFIC'] = pd.to_datetime(df_mun['DT_NOTIFIC'], errors='coerce')
        serie_temporal = df_mun.resample('W-Mon', on='DT_NOTIFIC').size().reset_index(name='y')
        serie_temporal.rename(columns={'DT_NOTIFIC': 'ds'}, inplace=True)

        # 2. Treinar o modelo Prophet
        modelo = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False, interval_width=0.95)
        modelo.fit(serie_temporal)

        # 3. Fazer a "previsão" sobre os próprios dados históricos
        previsao = modelo.predict(serie_temporal)

        # 4. Identificar as anomalias (quando o valor real excede o limite superior)
        resultado = pd.concat([serie_temporal.set_index('ds'), previsao.set_index('ds')], axis=1)
        resultado['anomalia'] = resultado['y'] > resultado['yhat_upper']

        df_alertas = resultado[resultado['anomalia']].copy()

        if not df_alertas.empty:
            print(f"     -> ALERTA! {len(df_alertas)} semanas com anomalias detectadas.")
            df_alertas['ID_MUNICIP'] = municipio
            df_alertas['MUNICIPIO'] = nome_municipio
            df_alertas.rename(columns={'y': 'CASOS_OBSERVADOS', 'yhat_upper': 'LIMIAR_ESPERADO'}, inplace=True)
            alertas_gerais.append(df_alertas[['ID_MUNICIP', 'MUNICIPIO', 'CASOS_OBSERVADOS', 'LIMIAR_ESPERADO']])

    if not alertas_gerais:
        print("✅ Nenhuma anomalia estatisticamente significante foi detectada.")
        return pd.DataFrame()

    df_final_alertas = pd.concat(alertas_gerais).reset_index().rename(columns={'ds': 'SEMANA_EPIDEMIOLOGICA'})
    return df_final_alertas

# Mapeamento de Sigla de UF para código IBGE (necessário para o filtro)
uf_map = {
    'RO': 11, 'AC': 12, 'AM': 13, 'RR': 14, 'PA': 15, 'AP': 16, 'TO': 17,
    'MA': 21, 'PI': 22, 'CE': 23, 'RN': 24, 'PB': 25, 'PE': 26, 'AL': 27,
    'SE': 28, 'BA': 29, 'MG': 31, 'ES': 32, 'RJ': 33, 'SP': 35, 'PR': 41,
    'SC': 42, 'RS': 43, 'MS': 50, 'MT': 51, 'GO': 52, 'DF': 53
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa o pipeline de detecção de surtos em séries temporais de doenças infecciosas.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--ufs", nargs="+", required=True, help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados históricos do SINAN a usar (recomenda-se >= 5 anos).")
    parser.add_argument("--agravo", type=str, default="DENG", help="Código do agravo do SINAN a ser analisado (ex: DENG, CHIK, SRAG).")
    parser.add_argument("--dir_saida", type=str, default="outputs/deteccao_surtos", help="Diretório para salvar o relatório de alertas.")

    args = parser.parse_args()

    # Pipeline
    df_raw = carregar_dados_sinan_historico(ufs=args.ufs, anos=args.anos, agravo=args.agravo)

    if df_raw is not None and not df_raw.empty:
        # Cria um mapa de código -> nome de município para os relatórios
        df_raw['ID_MUNICIP'] = df_raw['ID_MUNICIP'].astype(str)
        uf_map_nomes = dict(zip(df_raw['ID_MUNICIP'], df_raw['ID_MUNICIP'] + ' - ' + df_raw['SG_UF_NOT'].astype(str)))

        df_alertas = detectar_anomalias_por_municipio(df_raw, uf_map_nomes)

        if not df_alertas.empty:
            output_dir = Path(args.dir_saida)
            output_dir.mkdir(parents=True, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"relatorio_alertas_surtos_{args.agravo.lower()}_{ufs_str}_{anos_str}.csv"
            caminho_csv = output_dir / nome_arquivo

            df_alertas.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')

            print(f"\n📄 Relatório de alertas de surto salvo em: '{caminho_csv}'")
            print("\n--- Amostra do Relatório de Alertas Gerados ---")
            print(df_alertas.head(10).to_string())

            print("\n" + "="*80)
            print("🎉 PIPELINE DE DETECÇÃO DE SURTOS CONCLUÍDO! 🎉")
            print("="*80)
