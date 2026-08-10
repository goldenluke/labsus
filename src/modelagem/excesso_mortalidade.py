# -*- coding: utf-8 -*-
"""
======================================================================
  CÁLCULO DE EXCESSO DE MORTALIDADE (OBSERVADO vs. ESPERADO)
======================================================================
Metodologia clássica de vigilância em saúde, popularizada durante a
pandemia de COVID-19 (usada pela OMS, "The Economist" e institutos de
estatística nacionais): estima quantos óbitos MENSAIS seriam esperados
em um período, com base no padrão histórico (tendência + sazonalidade)
de um PERÍODO-BASE "normal", e compara com o número REALMENTE observado.
A diferença é o "excesso de mortalidade" — uma medida mais robusta do
impacto real de uma crise sanitária do que contar apenas óbitos
diretamente atribuídos a uma causa específica (que pode estar
subnotificada).

Método: regressão harmônica (tendência linear + termos de Fourier para
sazonalidade anual) ajustada no período-base; projeção com intervalo de
predição para o período de avaliação.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pysus.online_data.SIM import download as download_sim


def carregar_serie_mensal_obitos(uf: str, anos: list, cid_prefixos: list = None) -> pd.Series:
    contagens = []
    for ano in sorted(anos):
        print(f"[LOG] Baixando SIM para {uf}/{ano}...")
        try:
            downloaded = download_sim(states=uf, years=ano, groups=['CID10'])
            if isinstance(downloaded, list):
                if not downloaded:
                    print(f"  -> Nenhum dado disponível para {ano} (ainda não publicado).")
                    continue
                df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True)
            else:
                df = downloaded.to_dataframe()
        except Exception as e:
            print(f"  -> ❌ Falha ao baixar {ano}: {e}")
            continue
        if cid_prefixos:
            df = df[df['CAUSABAS'].astype(str).str.startswith(tuple(cid_prefixos))]
        df['DTOBITO'] = pd.to_datetime(df['DTOBITO'], format='%d%m%Y', errors='coerce')
        df = df.dropna(subset=['DTOBITO'])
        contagens.append(df.resample('MS', on='DTOBITO').size())

    if not contagens:
        raise ValueError("Nenhum dado de óbito pôde ser carregado para os anos informados.")
    serie = pd.concat(contagens).sort_index()
    serie = serie.asfreq('MS', fill_value=0)
    return serie


def construir_features_harmonicas(datas: pd.DatetimeIndex, t0) -> pd.DataFrame:
    t = np.array([(d.year - t0.year) * 12 + (d.month - t0.month) for d in datas], dtype=float)
    mes_angulo = 2 * np.pi * datas.month.values / 12
    return pd.DataFrame({
        'const': 1.0, 't': t,
        'seno1': np.sin(mes_angulo), 'cos1': np.cos(mes_angulo),
        'seno2': np.sin(2 * mes_angulo), 'cos2': np.cos(2 * mes_angulo),
    }, index=datas)


def ajustar_modelo_baseline(serie_base: pd.Series):
    t0 = serie_base.index[0]
    X = construir_features_harmonicas(serie_base.index, t0)
    modelo = sm.OLS(serie_base.values, X).fit()
    return modelo, t0


def calcular_excesso(modelo, t0, serie_avaliacao: pd.Series) -> pd.DataFrame:
    X_avaliacao = construir_features_harmonicas(serie_avaliacao.index, t0)
    previsao = modelo.get_prediction(X_avaliacao)
    resumo = previsao.summary_frame(alpha=0.05)

    df = pd.DataFrame({
        'OBSERVADO': serie_avaliacao.values,
        'ESPERADO': resumo['mean'].values,
        'ESPERADO_IC95_INFERIOR': resumo['obs_ci_lower'].values,
        'ESPERADO_IC95_SUPERIOR': resumo['obs_ci_upper'].values,
    }, index=serie_avaliacao.index)
    df['EXCESSO'] = df['OBSERVADO'] - df['ESPERADO']
    df['EXCESSO_PERCENTUAL'] = (df['EXCESSO'] / df['ESPERADO']) * 100
    df['ACIMA_DO_ESPERADO'] = df['OBSERVADO'] > df['ESPERADO_IC95_SUPERIOR']
    return df


def gerar_grafico(serie_base: pd.Series, df_excesso: pd.DataFrame, cid_nome: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(13, 6))
    plt.plot(serie_base.index, serie_base.values, color='grey', label='Período-base (histórico)', alpha=0.7)
    plt.plot(df_excesso.index, df_excesso['OBSERVADO'], color='black', label='Observado (período de avaliação)')
    plt.plot(df_excesso.index, df_excesso['ESPERADO'], color='#4575b4', linestyle='--', label='Esperado (modelo)')
    plt.fill_between(df_excesso.index, df_excesso['ESPERADO_IC95_INFERIOR'], df_excesso['ESPERADO_IC95_SUPERIOR'],
                      color='#4575b4', alpha=0.15, label='Intervalo de predição 95%')
    plt.fill_between(df_excesso.index, df_excesso['ESPERADO'], df_excesso['OBSERVADO'],
                      where=(df_excesso['OBSERVADO'] > df_excesso['ESPERADO']), color='#d73027', alpha=0.3, label='Excesso de mortalidade')
    plt.title(f"Excesso de Mortalidade — {cid_nome} em {uf}")
    plt.ylabel('Óbitos/mês')
    plt.legend()
    caminho_fig = dir_saida / f"excesso_mortalidade_{cid_nome.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    cid_nome = "Todas as Causas" if not args.cids else "-".join(args.cids)

    print(f"\n--- [ETAPA 1] Carregando série mensal de óbitos ({cid_nome}) — Período-base {args.anos_base} ---")
    serie_base = carregar_serie_mensal_obitos(args.uf, args.anos_base, args.cids)
    print(f"✅ Período-base com {len(serie_base)} meses.")

    print(f"\n--- [ETAPA 2] Carregando período de avaliação {args.anos_avaliacao} ---")
    serie_avaliacao = carregar_serie_mensal_obitos(args.uf, args.anos_avaliacao, args.cids)
    print(f"✅ Período de avaliação com {len(serie_avaliacao)} meses.")

    if len(serie_base) < 24:
        print("❌ Período-base muito curto para um modelo sazonal confiável (mínimo recomendado: 24 meses).")
        return

    print(f"\n--- [ETAPA 3] Ajustando modelo de baseline (tendência + sazonalidade harmônica) ---")
    modelo, t0 = ajustar_modelo_baseline(serie_base)
    print(f"✅ Modelo ajustado. R² (ajuste ao período-base): {modelo.rsquared:.3f}")

    df_excesso = calcular_excesso(modelo, t0, serie_avaliacao)

    excesso_total = df_excesso['EXCESSO'].sum()
    excesso_pct_medio = df_excesso['EXCESSO_PERCENTUAL'].mean()
    meses_acima = df_excesso['ACIMA_DO_ESPERADO'].sum()

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: EXCESSO DE MORTALIDADE — {cid_nome} EM {args.uf} ---")
    print("=" * 70)
    print(f"Óbitos observados no período de avaliação: {int(df_excesso['OBSERVADO'].sum())}")
    print(f"Óbitos esperados (baseline): {df_excesso['ESPERADO'].sum():.1f}")
    print(f"Excesso de mortalidade total: {excesso_total:.1f} óbitos ({excesso_pct_medio:+.1f}% em média)")
    print(f"Meses com óbitos significativamente acima do esperado: {meses_acima} de {len(df_excesso)}")
    print("=" * 70)

    caminho_csv = dir_saida / f"excesso_mortalidade_{cid_nome.lower().replace(' ', '_')}_{args.uf.lower()}.csv"
    df_excesso.to_csv(caminho_csv, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resultado mês a mês salvo em: '{caminho_csv}'")

    gerar_grafico(serie_base, df_excesso, cid_nome, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 CÁLCULO DE EXCESSO DE MORTALIDADE CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula o excesso de mortalidade comparando um período de avaliação com um período-base histórico.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos-base", nargs="+", type=int, required=True, help="Anos do período-base 'normal' (ex: 2015 2016 2017 2018 2019).")
    parser.add_argument("--anos-avaliacao", nargs="+", type=int, required=True, help="Anos do período a avaliar (ex: 2020 2021).")
    parser.add_argument("--cids", nargs="+", default=None, help="Prefixos de CID-10 (ex: J1 para pneumonias). Se omitido, considera todas as causas.")
    parser.add_argument("--dir_saida", type=str, default="outputs/excesso_mortalidade", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
