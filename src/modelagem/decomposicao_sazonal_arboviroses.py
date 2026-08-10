# -*- coding: utf-8 -*-
"""
======================================================================
  DECOMPOSIÇÃO SAZONAL (STL) E PREVISÃO (SARIMA) DE ARBOVIROSES
======================================================================
Este script decompõe a série histórica MENSAL de casos de um agravo do
SINAN (por padrão, Dengue) em três componentes — TENDÊNCIA (aumento ou
queda estrutural ao longo dos anos), SAZONALIDADE (o padrão que se repete
todo ano, tipicamente picos no verão/período chuvoso) e RESÍDUO (o que
sobra, incluindo possíveis surtos atípicos) — usando STL (Seasonal-Trend
decomposition using LOESS). Em seguida, ajusta um modelo SARIMA
(auto-regressivo sazonal) sobre a série completa para projetar os
próximos meses com intervalo de confiança.

Diferente do Prophet usado em outros scripts do projeto, o STL+SARIMA é
a abordagem clássica de séries temporais (Box-Jenkins) — mais
transparente sobre as premissas estatísticas e mais adequada quando se
quer isolar e quantificar CADA componente da série separadamente.
"""

import argparse
from pathlib import Path

import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX

UF_PARA_CODIGO_IBGE = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17',
    'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27',
    'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41',
    'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53',
}


def carregar_serie_mensal(dis_code: str, uf: str, anos: list) -> pd.Series:
    from pysus.online_data.SINAN import SINAN

    sinan_db = SINAN().load()
    files = sinan_db.get_files(dis_code=dis_code, year=anos)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo SINAN/{dis_code} encontrado para {anos}.")
    downloaded = sinan_db.download(files)
    df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()

    codigo_uf = UF_PARA_CODIGO_IBGE[uf.upper()]
    if 'ID_MN_RESI' in df.columns:
        df = df[df['ID_MN_RESI'].astype(str).str[:2] == codigo_uf].copy()

    col_data = 'DT_SIN_PRI' if 'DT_SIN_PRI' in df.columns else 'DT_NOTIFIC'
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
    df = df.dropna(subset=[col_data])

    serie = df.resample('MS', on=col_data).size()
    serie = serie.asfreq('MS', fill_value=0)
    return serie


def decompor_stl(serie: pd.Series, periodo: int = 12):
    stl = STL(serie, period=periodo, robust=True)
    resultado = stl.fit()
    return resultado


def prever_sarima(serie: pd.Series, ordem, ordem_sazonal, passos_futuros: int):
    modelo = SARIMAX(serie, order=ordem, seasonal_order=ordem_sazonal,
                      enforce_stationarity=False, enforce_invertibility=False)
    resultado = modelo.fit(disp=False)
    previsao = resultado.get_forecast(steps=passos_futuros)
    return resultado, previsao


def gerar_grafico_stl(stl_resultado, serie: pd.Series, dis_code: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=True)
    axes[0].plot(serie.index, serie.values, color='black')
    axes[0].set_title(f'Casos observados — SINAN/{dis_code} em {uf}')
    axes[1].plot(stl_resultado.trend.index, stl_resultado.trend.values, color='#d73027')
    axes[1].set_title('Tendência')
    axes[2].plot(stl_resultado.seasonal.index, stl_resultado.seasonal.values, color='#4575b4')
    axes[2].set_title('Sazonalidade')
    axes[3].scatter(stl_resultado.resid.index, stl_resultado.resid.values, color='grey', s=10)
    axes[3].axhline(0, color='black', linewidth=0.8)
    axes[3].set_title('Resíduo (possíveis surtos atípicos)')
    plt.tight_layout()
    caminho_fig = dir_saida / f"stl_decomposicao_{dis_code.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150)
    plt.close()
    print(f"📈 Gráfico de decomposição STL salvo em: {caminho_fig}")


def gerar_grafico_previsao(serie: pd.Series, previsao, dis_code: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    ic = previsao.conf_int()
    plt.figure(figsize=(13, 6))
    plt.plot(serie.index, serie.values, label='Observado', color='black')
    plt.plot(previsao.predicted_mean.index, previsao.predicted_mean.values, label='Previsão (SARIMA)', color='#d73027')
    plt.fill_between(ic.index, ic.iloc[:, 0], ic.iloc[:, 1], color='#d73027', alpha=0.2, label='Intervalo de confiança 95%')
    plt.title(f'Previsão SARIMA — SINAN/{dis_code} em {uf}')
    plt.legend()
    caminho_fig = dir_saida / f"sarima_previsao_{dis_code.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de previsão SARIMA salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando série mensal de SINAN/{args.dis_code} para {args.uf}/{args.anos} ---")
    serie = carregar_serie_mensal(args.dis_code, args.uf, args.anos)
    print(f"✅ Série com {len(serie)} meses, {serie.sum()} casos totais.")

    if len(serie) < 24:
        print("❌ Série muito curta para decomposição sazonal confiável (mínimo recomendado: 24 meses / 2 anos).")
        return

    print(f"\n--- [ETAPA 2] Decompondo a série (STL) ---")
    stl_resultado = decompor_stl(serie)
    gerar_grafico_stl(stl_resultado, serie, args.dis_code, args.uf, dir_saida)

    print(f"\n--- [ETAPA 3] Ajustando SARIMA{tuple(args.ordem)}x{tuple(args.ordem_sazonal)} e prevendo {args.meses_futuros} meses ---")
    ordem_sazonal = tuple(args.ordem_sazonal) + (12,)
    resultado_sarima, previsao = prever_sarima(serie, tuple(args.ordem), ordem_sazonal, args.meses_futuros)

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: PREVISÃO SARIMA — SINAN/{args.dis_code} EM {args.uf} ---")
    print("=" * 70)
    print(f"AIC do modelo: {resultado_sarima.aic:.1f}")
    print(previsao.predicted_mean.round(1).to_string())
    print("=" * 70)

    gerar_grafico_previsao(serie, previsao, args.dis_code, args.uf, dir_saida)

    df_saida = pd.DataFrame({
        'DATA': serie.index, 'CASOS_OBSERVADOS': serie.values,
        'TENDENCIA': stl_resultado.trend.values, 'SAZONALIDADE': stl_resultado.seasonal.values,
        'RESIDUO': stl_resultado.resid.values,
    })
    caminho_csv = dir_saida / f"decomposicao_{args.dis_code.lower()}_{args.uf.lower()}.csv"
    df_saida.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Decomposição salva em: '{caminho_csv}'")

    df_previsao = previsao.summary_frame()
    caminho_csv_prev = dir_saida / f"previsao_{args.dis_code.lower()}_{args.uf.lower()}.csv"
    df_previsao.to_csv(caminho_csv_prev, sep=';', encoding='utf-8-sig')
    print(f"📄 Previsão salva em: '{caminho_csv_prev}'")

    print("\n" + "=" * 80)
    print("🎉 DECOMPOSIÇÃO SAZONAL E PREVISÃO CONCLUÍDAS! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decompõe (STL) e prevê (SARIMA) a série mensal de um agravo do SINAN.")
    parser.add_argument("--dis-code", type=str, default="DENG", help="Código do agravo do SINAN (ex: DENG, CHIK, ZIKA).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados históricos (recomenda-se >= 3 anos).")
    parser.add_argument("--ordem", nargs=3, type=int, default=[1, 1, 1], help="Ordem (p,d,q) do SARIMA.")
    parser.add_argument("--ordem-sazonal", nargs=3, type=int, default=[1, 1, 1], help="Ordem sazonal (P,D,Q) do SARIMA (período fixo em 12 meses).")
    parser.add_argument("--meses-futuros", type=int, default=6, help="Nº de meses a prever no futuro.")
    parser.add_argument("--dir_saida", type=str, default="outputs/stl_sarima_arboviroses", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
