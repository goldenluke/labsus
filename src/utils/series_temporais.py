# -*- coding: utf-8 -*-
"""
Helpers compartilhados por scripts de previsão de séries temporais mensais
(Prophet) — evita repetir o mesmo ajuste/previsão/gráfico em cada um dos
módulos de "Previsão de Óbitos", "Previsão de Nascimentos" e "Previsão de
Produção Ambulatorial", que só diferem na fonte de dados (SIM/SINASC/SIA).
"""
from pathlib import Path

import pandas as pd


def prever_serie_mensal_prophet(serie: pd.Series, meses_futuros: int, yearly_seasonality: bool = True) -> pd.DataFrame:
    """Ajusta Prophet a uma série mensal (index=Timestamp mensal, values=contagem)
    e retorna um DataFrame curado (ds, y, yhat, yhat_lower, yhat_upper) cobrindo
    o histórico + meses_futuros à frente. Previsões negativas são zeradas —
    contagens de eventos não podem ser negativas."""
    from prophet import Prophet

    df_hist = serie.rename('y').rename_axis('ds').reset_index()
    modelo = Prophet(yearly_seasonality=yearly_seasonality, weekly_seasonality=False, daily_seasonality=False)
    modelo.fit(df_hist)

    futuro = modelo.make_future_dataframe(periods=meses_futuros, freq='MS')
    previsao = modelo.predict(futuro)

    resultado = previsao[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].merge(df_hist, on='ds', how='left')
    for col in ['yhat', 'yhat_lower', 'yhat_upper']:
        resultado[col] = resultado[col].clip(lower=0)
    return resultado[['ds', 'y', 'yhat', 'yhat_lower', 'yhat_upper']]


def gerar_grafico_previsao_prophet(df_previsao: pd.DataFrame, titulo: str, caminho_fig: Path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df_previsao['ds'], df_previsao['y'], label='Observado', color='black', marker='o', markersize=3)
    ax.plot(df_previsao['ds'], df_previsao['yhat'], label='Previsão (Prophet)', color='#d73027')
    ax.fill_between(df_previsao['ds'], df_previsao['yhat_lower'], df_previsao['yhat_upper'],
                     color='#d73027', alpha=0.2, label='Intervalo de incerteza')
    ax.set_title(titulo)
    ax.set_ylabel('Contagem mensal')
    ax.legend()
    plt.tight_layout()
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
