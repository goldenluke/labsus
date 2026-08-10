# -*- coding: utf-8 -*-
"""
======================================================================
  DESENHO DE DESCONTINUIDADE DE REGRESSÃO (RDD) NO LIMIAR DE 2.500g
======================================================================
Aplica o desenho de pesquisa "Regression Discontinuity" (RDD) — um dos
métodos mais respeitados de inferência causal com dados observacionais —
ao limiar clínico de 2.500g que separa "peso normal" de "baixo peso ao
nascer" no SINASC. Este limiar é usado mundialmente (inclusive no Brasil)
para desencadear PROTOCOLOS DE CUIDADO ADICIONAL (triagem mais intensiva,
prioridade de leito, acompanhamento diferenciado) — criando um
"experimento natural": um bebê nascido com 2.499g recebe, na prática,
tratamento clínico sistematicamente diferente de um nascido com 2.501g,
mesmo os dois sendo clinicamente quase idênticos. Comparando o desfecho
(óbito infantil) BEM PERTO dos dois lados do limiar, isola-se o efeito do
"tratamento adicional" da simples diferença de gravidade clínica.

Referência: desenho popularizado por Almond, Doyle, Kowalski & Williams
(2010, QJE) para o mesmo limiar em dados dos EUA.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

from src.modelagem.analise_sobrevida_infantil import carregar_dados, vincular_obitos_real

LIMIAR_BAIXO_PESO = 2500


def preparar_dados_rdd(uf: str, ano: int, banda_gramas: int) -> pd.DataFrame:
    df_sinasc, df_sim, df_cnes = carregar_dados(ufs=[uf], ano_coorte=ano)
    if df_sinasc is None or df_sinasc.empty:
        raise ValueError("Não foi possível carregar dados do SINASC.")

    df_vinculado = vincular_obitos_real(df_sinasc, df_sim)

    df_vinculado['PESO'] = pd.to_numeric(df_vinculado['PESO'], errors='coerce')
    df = df_vinculado.dropna(subset=['PESO', 'OBITO_INFANTIL']).copy()

    df = df[(df['PESO'] >= LIMIAR_BAIXO_PESO - banda_gramas) & (df['PESO'] <= LIMIAR_BAIXO_PESO + banda_gramas)]
    df['PESO_CENTRADO'] = df['PESO'] - LIMIAR_BAIXO_PESO
    df['ABAIXO_LIMIAR'] = (df['PESO'] < LIMIAR_BAIXO_PESO).astype(int)
    df['INTERACAO'] = df['ABAIXO_LIMIAR'] * df['PESO_CENTRADO']
    return df


def ajustar_rdd(df: pd.DataFrame):
    """Regressão linear local (um dos lados de cada vez, via termo de interação):
    OBITO = β0 + β1*ABAIXO_LIMIAR + β2*PESO_CENTRADO + β3*(ABAIXO_LIMIAR × PESO_CENTRADO)."""
    modelo = smf.ols('OBITO_INFANTIL ~ ABAIXO_LIMIAR + PESO_CENTRADO + INTERACAO', data=df).fit(cov_type='HC1')
    return modelo


def gerar_grafico_rdd(df: pd.DataFrame, dir_saida: Path, uf: str, largura_bin: int = 25):
    plt.figure(figsize=(11, 7))
    df_plot = df.copy()
    df_plot['BIN'] = (df_plot['PESO'] // largura_bin) * largura_bin + largura_bin / 2
    medias_bin = df_plot.groupby('BIN')['OBITO_INFANTIL'].agg(['mean', 'count']).reset_index()
    medias_bin = medias_bin[medias_bin['count'] >= 3]

    plt.scatter(medias_bin['BIN'], medias_bin['mean'], s=medias_bin['count'], alpha=0.6, edgecolor='k',
                label='Taxa de óbito observada (por faixa de peso)')

    for lado, cor in [(1, '#d73027'), (0, '#4575b4')]:
        sub = df[df['ABAIXO_LIMIAR'] == lado]
        if len(sub) < 5:
            continue
        modelo_lado = smf.ols('OBITO_INFANTIL ~ PESO_CENTRADO', data=sub).fit()
        xs = np.linspace(sub['PESO_CENTRADO'].min(), sub['PESO_CENTRADO'].max(), 50)
        ys = modelo_lado.predict(pd.DataFrame({'PESO_CENTRADO': xs}))
        plt.plot(xs + LIMIAR_BAIXO_PESO, ys, color=cor, linewidth=2.5)

    plt.axvline(LIMIAR_BAIXO_PESO, color='black', linestyle='--', label=f'Limiar clínico ({LIMIAR_BAIXO_PESO}g)')
    plt.xlabel('Peso ao nascer (gramas)')
    plt.ylabel('Taxa de óbito infantil')
    plt.title(f'Descontinuidade no Limiar de Baixo Peso — {uf}')
    plt.legend()
    caminho_fig = dir_saida / f"rdd_peso_nascer_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de descontinuidade salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando e vinculando nascimentos/óbitos para {args.uf}/{args.ano} (banda: ±{args.banda}g) ---")
    df = preparar_dados_rdd(args.uf, args.ano, args.banda)
    print(f"✅ {len(df)} nascimentos na banda de {LIMIAR_BAIXO_PESO - args.banda}g–{LIMIAR_BAIXO_PESO + args.banda}g.")

    if len(df) < 200:
        print("❌ Poucas observações na banda para uma estimativa RDD confiável (mínimo recomendado: 200). Tente aumentar --banda.")
        return

    print(f"\n--- [ETAPA 2] Ajustando a regressão local (RDD) ---")
    modelo = ajustar_rdd(df)

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: DESCONTINUIDADE NO LIMIAR DE {LIMIAR_BAIXO_PESO}g EM {args.uf} ---")
    print("=" * 80)
    print(modelo.summary())

    efeito = modelo.params['ABAIXO_LIMIAR']
    p_valor = modelo.pvalues['ABAIXO_LIMIAR']
    ic = modelo.conf_int().loc['ABAIXO_LIMIAR']
    print("\n--- INTERPRETAÇÃO ---")
    print(f"Salto na taxa de óbito infantil bem no limiar (efeito 'tratamento adicional'): {efeito:+.4f}")
    print(f"Intervalo de confiança 95%: [{ic[0]:+.4f}, {ic[1]:+.4f}]  |  p-valor: {p_valor:.4f}")
    if p_valor < 0.05 and efeito < 0:
        print("✅ Bebês logo ABAIXO do limiar (que recebem cuidado adicional) têm taxa de óbito significativamente MENOR do que a extrapolação da tendência sugeriria — evidência de que o protocolo de cuidado adicional salva vidas.")
    elif p_valor < 0.05 and efeito > 0:
        print("⚠️ Salto na direção inesperada (maior mortalidade logo abaixo do limiar) — investigar possível viés de manipulação do registro de peso ('heaping') ou outro fator de confusão.")
    else:
        print("⚠️ Não há evidência estatística de descontinuidade no desfecho exatamente no limiar clínico.")
    print("=" * 80)

    caminho_csv = dir_saida / f"rdd_peso_nascer_{args.uf.lower()}.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Dados da banda salvos em: '{caminho_csv}'")

    gerar_grafico_rdd(df, dir_saida, args.uf)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE DESCONTINUIDADE DE REGRESSÃO CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estima o efeito causal do limiar clínico de baixo peso (2.500g) via Regressão Descontínua (RDD).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano da coorte de nascimentos.")
    parser.add_argument("--banda", type=int, default=300, help="Banda (largura, em gramas) ao redor do limiar de 2.500g a considerar na análise.")
    parser.add_argument("--dir_saida", type=str, default="outputs/rdd_peso_nascer", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
