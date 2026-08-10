# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE KOTELCHUCK (APNCU) DE ADEQUAÇÃO DO PRÉ-NATAL (SINASC)
======================================================================
Implementa o Índice de Adequação da Utilização do Pré-Natal de Kotelchuck
(APNCU) — ver Apêndice D do dicionário de dados do projeto — que combina
DUAS dimensões (diferente de olhar isoladamente para o número de
consultas, como a maioria das análises faz): (1) o MÊS de início do
pré-natal (MESPRENAT) e (2) a RAZÃO entre o número de consultas
observadas (CONSPRENAT) e o número esperado pelas diretrizes do ACOG,
ajustado pela idade gestacional do parto e por quantas consultas já
"passaram" antes do início efetivo do pré-natal.

Limitação assumida (documentada explicitamente no código): o SINASC
registra CONSPRENAT em FAIXAS (1=Nenhuma, 2=1-3, 3=4-6, 4=7+), não o
número exato de consultas. Este script usa o valor representativo de
cada faixa (0, 2, 5, 8) como aproximação do número observado — suficiente
para aplicar corretamente a REGRA DE CLASSIFICAÇÃO do índice (o objetivo
central deste script), ainda que introduza alguma imprecisão na razão
calculada em casos limítrofes.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from pysus.online_data.SINASC import download as download_sinasc

# Calendário padrão de consultas esperadas por mês de gestação (ACOG),
# reconstruído a partir do exemplo do dicionário de dados ("parto de 40
# semanas -> 14 consultas esperadas; início no 4º mês -> 11 esperadas
# após desconto de 3 consultas 'perdidas'"): 1 consulta/mês do 1º ao 6º
# mês, 2 consultas no 7º e 8º mês, 4 consultas (semanais) no 9º mês.
VISITAS_POR_MES = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 4}
CONSULTAS_ESPERADAS_ACUMULADAS = {0: 0}
_acumulado = 0
for _mes in range(1, 10):
    _acumulado += VISITAS_POR_MES[_mes]
    CONSULTAS_ESPERADAS_ACUMULADAS[_mes] = _acumulado

MAPA_CONSPRENAT_PARA_CONTAGEM = {1: 0, 2: 2, 3: 5, 4: 8}


def carregar_nascimentos(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
    downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
    df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    return df


def mes_de_gestacao_do_parto(semanas: float) -> int:
    if pd.isna(semanas) or semanas <= 0:
        return np.nan
    return int(min(9, np.ceil(semanas / 4.345)))


def calcular_kotelchuck(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ['MESPRENAT', 'CONSPRENAT']:
        if col not in df.columns:
            raise KeyError(f"Coluna '{col}' (necessária para o Índice de Kotelchuck) não encontrada no SINASC.")
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'SEMAGESTAC' in df.columns:
        df['SEMANAS_GESTACAO'] = pd.to_numeric(df['SEMAGESTAC'], errors='coerce')
    else:
        mapa_semanas_midpoint = {1: 18, 2: 24, 3: 29, 4: 34, 5: 39, 6: 42}
        df['SEMANAS_GESTACAO'] = pd.to_numeric(df['GESTACAO'], errors='coerce').map(mapa_semanas_midpoint)

    df = df.dropna(subset=['MESPRENAT', 'CONSPRENAT', 'SEMANAS_GESTACAO'])
    df = df[df['MESPRENAT'].between(1, 9) & df['CONSPRENAT'].between(1, 4)]

    df['MES_PARTO'] = df['SEMANAS_GESTACAO'].apply(mes_de_gestacao_do_parto)
    df = df.dropna(subset=['MES_PARTO'])
    df['MES_PARTO'] = df['MES_PARTO'].astype(int)
    df['MESPRENAT'] = df['MESPRENAT'].astype(int)

    df['CONSULTAS_OBSERVADAS_APROX'] = df['CONSPRENAT'].map(MAPA_CONSPRENAT_PARA_CONTAGEM)
    df['CONSULTAS_ESPERADAS_TOTAL'] = df['MES_PARTO'].map(CONSULTAS_ESPERADAS_ACUMULADAS)
    df['CONSULTAS_PERDIDAS_ANTES_INICIO'] = (df['MESPRENAT'] - 1).clip(lower=0).map(CONSULTAS_ESPERADAS_ACUMULADAS)
    df['CONSULTAS_ESPERADAS_AJUSTADAS'] = (df['CONSULTAS_ESPERADAS_TOTAL'] - df['CONSULTAS_PERDIDAS_ANTES_INICIO']).clip(lower=1)
    df['RAZAO_ADEQUACAO_PCT'] = (df['CONSULTAS_OBSERVADAS_APROX'] / df['CONSULTAS_ESPERADAS_AJUSTADAS']) * 100

    def classificar(row):
        if row['CONSPRENAT'] == 1:
            return 'Sem Pré-Natal'
        inicio_tardio = row['MESPRENAT'] >= 5
        if inicio_tardio or row['RAZAO_ADEQUACAO_PCT'] < 50:
            return 'Inadequado'
        if row['RAZAO_ADEQUACAO_PCT'] < 80:
            return 'Intermediário'
        if row['RAZAO_ADEQUACAO_PCT'] < 110:
            return 'Adequado'
        return 'Mais que Adequado'

    df['KOTELCHUCK'] = df.apply(classificar, axis=1)
    return df


def associar_a_desfechos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['PESO'] = pd.to_numeric(df.get('PESO'), errors='coerce')
    df['BAIXO_PESO'] = (df['PESO'] < 2500).astype('Int64')
    df['PREMATURO'] = pd.to_numeric(df.get('GESTACAO'), errors='coerce').apply(lambda g: 1 if g in (1, 2, 3, 4) else (0 if pd.notna(g) else pd.NA)).astype('Int64')

    ordem = ['Sem Pré-Natal', 'Inadequado', 'Intermediário', 'Adequado', 'Mais que Adequado']
    resumo = df.groupby('KOTELCHUCK').agg(
        N_NASCIMENTOS=('KOTELCHUCK', 'size'),
        PERC_BAIXO_PESO=('BAIXO_PESO', 'mean'),
        PERC_PREMATURIDADE=('PREMATURO', 'mean'),
    ).reindex(ordem).dropna(how='all')
    resumo['PERC_BAIXO_PESO'] *= 100
    resumo['PERC_PREMATURIDADE'] *= 100
    return resumo


def gerar_grafico(resumo: pd.DataFrame, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(resumo))
    largura = 0.35
    ax.bar(x - largura / 2, resumo['PERC_BAIXO_PESO'], largura, label='% Baixo Peso ao Nascer', color='#d73027')
    ax.bar(x + largura / 2, resumo['PERC_PREMATURIDADE'], largura, label='% Prematuridade', color='#4575b4')
    ax.set_xticks(x)
    ax.set_xticklabels(resumo.index, rotation=20, ha='right')
    ax.set_ylabel('% dos nascimentos')
    ax.set_title(f'Desfechos Perinatais por Categoria do Índice de Kotelchuck — {uf}')
    ax.legend()
    caminho_fig = dir_saida / f"kotelchuck_desfechos_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando nascimentos para {args.uf}/{args.ano} ---")
    df_raw = carregar_nascimentos(args.uf, args.ano)
    print(f"✅ {len(df_raw)} nascimentos carregados.")

    print(f"\n--- [ETAPA 2] Calculando o Índice de Kotelchuck (APNCU) ---")
    df = calcular_kotelchuck(df_raw)
    print(f"✅ {len(df)} nascimentos classificados.")

    if len(df) < 50:
        print("❌ Poucos nascimentos para uma análise confiável (mínimo recomendado: 50).")
        return

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: DISTRIBUIÇÃO DO ÍNDICE DE KOTELCHUCK EM {args.uf}/{args.ano} ---")
    print("=" * 80)
    distribuicao = df['KOTELCHUCK'].value_counts(normalize=True).reindex(
        ['Sem Pré-Natal', 'Inadequado', 'Intermediário', 'Adequado', 'Mais que Adequado']).dropna() * 100
    print(distribuicao.round(1).to_string())
    print("=" * 80)

    print(f"\n--- [ETAPA 3] Associando classificação a desfechos perinatais ---")
    resumo = associar_a_desfechos(df)
    print("\n--- Desfechos por categoria do Índice de Kotelchuck ---")
    print(resumo.round(2).to_string())

    caminho_csv = dir_saida / f"kotelchuck_{args.uf.lower()}_{args.ano}.csv"
    df[['MESPRENAT', 'CONSPRENAT', 'MES_PARTO', 'RAZAO_ADEQUACAO_PCT', 'KOTELCHUCK']].to_csv(
        caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Classificação individual salva em: '{caminho_csv}'")

    caminho_resumo = dir_saida / f"kotelchuck_desfechos_{args.uf.lower()}_{args.ano}.csv"
    resumo.to_csv(caminho_resumo, sep=';', encoding='utf-8-sig')
    print(f"📄 Resumo de desfechos por categoria salvo em: '{caminho_resumo}'")

    gerar_grafico(resumo, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 CÁLCULO DO ÍNDICE DE KOTELCHUCK CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula o Índice de Kotelchuck (APNCU) de adequação do pré-natal e o associa a desfechos perinatais.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--dir_saida", type=str, default="outputs/indice_kotelchuck", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
