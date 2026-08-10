# -*- coding: utf-8 -*-
"""
======================================================================
  PREVISÃO DE DEMANDA DE NASCIMENTOS ESTRATIFICADA POR RISCO PERINATAL
======================================================================
Este script implementa um pipeline de Machine Learning para prever a
demanda futura de nascimentos, separando a previsão em dois estratos:
nascimentos de "alto risco" e de "baixo/moderado risco".
"""

import pandas as pd
from pathlib import Path
import argparse
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

# Importações do PySUS
from pysus.online_data.SINASC import SINASC


# Ferramentas de Forecasting e Modelagem
from prophet import Prophet

# Reutilizando a função de preparação de dados do modelo de risco
try:
    from src.modelagem.modelo_risco_perinatal import preparar_dados
except ImportError:
    print("ERRO: Certifique-se de que este script está na mesma pasta que 'modelo_risco_perinatal.py'")
    preparar_dados = None

def carregar_dados_sinasc_historico(ufs: list, anos: list) -> pd.DataFrame:
    """Baixa uma longa série histórica de dados do SINASC."""
    print(f"\n--- [ETAPA 1] Carregando série histórica do SINASC para {ufs}/{anos} ---")

    try:
        sinasc_db = SINASC().load()
        files = sinasc_db.get_files(group='DN', uf=ufs, year=anos)
        if not files:
            print("⚠️ Nenhum arquivo SINASC encontrado para os filtros fornecidos.")
            return pd.DataFrame()

        print(f"[LOG] Baixando e processando {len(files)} arquivo(s)...")
        downloaded = sinasc_db.download(files)
        if isinstance(downloaded, list):
            df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True)
        elif hasattr(downloaded, "to_dataframe"):
            df = downloaded.to_dataframe()
        else:
            df = pd.DataFrame()

        print(f"✅ Série histórica do SINASC carregada com sucesso. Total de {len(df)} registros.")
        return df
    except Exception as e:
        print(f"❌ Erro crítico durante o carregamento de dados do SINASC: {e}")
        return pd.DataFrame()

def estratificar_nascimentos_por_risco(df_historico: pd.DataFrame, caminho_modelo: Path, limiar_risco: float):
    """Aplica o modelo de risco perinatal para classificar cada nascimento."""
    print("\n--- [ETAPA 2] Estratificando nascimentos históricos por risco ---")

    try:
        modelo_risco = joblib.load(caminho_modelo)
        print(f"[LOG] Modelo de risco carregado de '{caminho_modelo.name}'.")
    except FileNotFoundError:
        print(f"❌ ERRO: Modelo não encontrado em '{caminho_modelo}'."); return None

    if preparar_dados is None: return None
    X, _ = preparar_dados(df_historico)

    if X.empty:
        print("❌ Nenhum dado válido restante após a preparação. Abortando."); return None

    print("[LOG] Calculando scores de risco para todos os registros...")
    scores_risco = modelo_risco.predict_proba(X)[:, 1]

    df_com_risco = df_historico.loc[X.index].copy()
    df_com_risco['SCORE_RISCO'] = scores_risco
    df_com_risco['CLASSIF_RISCO'] = (df_com_risco['SCORE_RISCO'] > limiar_risco).map({True: 'Alto Risco', False: 'Baixo/Moderado Risco'})

    print("✅ Nascimentos históricos estratificados com sucesso.")
    return df_com_risco

def prever_demanda_estratificada(df: pd.DataFrame, meses_previsao: int):
    """Cria e treina modelos Prophet para cada estrato de risco."""
    print("\n--- [ETAPA 3] Treinando modelos de previsão de demanda ---")

    df['DATA'] = pd.to_datetime(df['DTNASC'], format='%d%m%Y', errors='coerce')
    df.dropna(subset=['DATA'], inplace=True)

    previsoes = {}
    dados_historicos = {}

    for risco, grupo_df in df.groupby('CLASSIF_RISCO'):
        print(f"  -> Treinando modelo para o estrato: '{risco}'...")

        serie_temporal = grupo_df.resample('ME', on='DATA').size().reset_index(name='y')
        serie_temporal.rename(columns={'DATA': 'ds'}, inplace=True)

        dados_historicos[risco] = serie_temporal.copy()

        modelo = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        modelo.fit(serie_temporal)

        futuro = modelo.make_future_dataframe(periods=meses_previsao, freq='ME')
        previsao = modelo.predict(futuro)

        previsoes[risco] = previsao
        print(f"     -> Previsão para '{risco}' concluída.")

    return previsoes, dados_historicos

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prevê a demanda de nascimentos estratificada por risco perinatal.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos-historico", nargs="+", type=int, required=True, help="Lista de anos de dados históricos do SINASC (recomenda-se >= 5 anos).")
    parser.add_argument("--meses-futuros", type=int, default=12, help="Número de meses a prever no futuro.")
    parser.add_argument("--modelo-risco", type=str, default="outputs/risco_perinatal/modelo_risco_perinatal.joblib", help="Caminho para o modelo de risco perinatal treinado.")
    parser.add_argument("--limiar-risco", type=float, default=0.5, help="Limiar de probabilidade para classificar um nascimento como 'Alto Risco'.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsao_demanda_estratificada", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    df_historico_raw = carregar_dados_sinasc_historico(ufs=args.ufs, anos=args.anos_historico)

    if df_historico_raw is not None and not df_historico_raw.empty:
        df_estratificado = estratificar_nascimentos_por_risco(df_historico_raw, Path(args.modelo_risco), args.limiar_risco)

        if df_estratificado is not None and not df_estratificado.empty:
            previsoes_por_risco, historicos_por_risco = prever_demanda_estratificada(df_estratificado, args.meses_futuros)

            output_dir = Path(args.dir_saida)
            output_dir.mkdir(parents=True, exist_ok=True)

            df_final_previsao = pd.DataFrame()

            # ==========================================================
            # --- SEÇÃO DE PLOTAGEM APRIMORADA ---
            # ==========================================================
            sns.set_style("whitegrid")
            fig, ax = plt.subplots(figsize=(14, 8))

            cores = {'Alto Risco': '#d9534f', 'Baixo/Moderado Risco': '#5bc0de'}

            for risco, previsao_df in previsoes_por_risco.items():
                cor = cores[risco]
                historico_df = historicos_por_risco[risco]

                # Plotar a linha da previsão (yhat)
                ax.plot(previsao_df['ds'], previsao_df['yhat'], color=cor, linestyle='-', lw=2, label=f'Previsão ({risco})')

                # Plotar a área de incerteza (yhat_lower, yhat_upper)
                ax.fill_between(
                    previsao_df['ds'],
                    previsao_df['yhat_lower'],
                    previsao_df['yhat_upper'],
                    color=cor,
                    alpha=0.2,
                    label=f'Intervalo de Confiança ({risco})'
                )

                # Plotar os pontos de dados históricos (y)
                ax.scatter(historico_df['ds'], historico_df['y'], color=cor, s=20, label=f'Histórico ({risco})', ec='black', zorder=5)

                # Consolida o CSV
                col_rename = {
                    'yhat': f'previsao_{risco.replace("/", "_").lower()}',
                    'yhat_lower': f'limite_inferior_{risco.replace("/", "_").lower()}',
                    'yhat_upper': f'limite_superior_{risco.replace("/", "_").lower()}',
                }
                previsao_df_renamed = previsao_df.rename(columns=col_rename)[['ds'] + list(col_rename.values())]

                if df_final_previsao.empty:
                    df_final_previsao = previsao_df_renamed
                else:
                    df_final_previsao = pd.merge(df_final_previsao, previsao_df_renamed, on='ds', how='outer')

            caminho_csv = output_dir / "previsao_demanda_estratificada.csv"
            df_final_previsao.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
            print(f"\n📄 Previsão consolidada salva em: '{caminho_csv}'")

            ax.set_title("Previsão de Demanda de Nascimentos por Estrato de Risco", fontsize=16)
            ax.set_xlabel('Data', fontsize=12)
            ax.set_ylabel('Nº de Nascimentos Mensais', fontsize=12)
            ax.legend()
            ax.grid(True, which='both', linestyle='--', linewidth=0.5)

            caminho_fig = output_dir / "grafico_previsao_demanda_estratificada.png"
            fig.savefig(caminho_fig, dpi=150, bbox_inches='tight')
            plt.close(fig)
            print(f"📈 Gráfico com as previsões salvo em: '{caminho_fig}'")
            # ==========================================================

            print("\n" + "="*80)
            print("🎉 PIPELINE DE PREVISÃO ESTRATIFICADA CONCLUÍDO! 🎉")
            print("="*80)
