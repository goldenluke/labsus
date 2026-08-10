# -*- coding: utf-8 -*-
"""
======================================================================
  SOBREVIDA LIVRE DE REINCIDÊNCIA POR CAUSAS EXTERNAS (TRAUMA/VIOLÊNCIA)
======================================================================
Causas externas (Capítulo XX da CID-10: acidentes, agressões, lesões
autoprovocadas — CID V, W, X, Y) têm um padrão clínico bem documentado de
RECORRÊNCIA: um paciente internado uma vez por trauma tem risco elevado
de uma nova internação pelo mesmo motivo (accidente de repetição,
violência doméstica recorrente, tentativas repetidas de autoextermínio).

Este script identifica, no SIH, pacientes com pseudo-ID consistente
(nascimento+sexo+município) que tiveram MAIS DE UMA internação por causa
externa, e modela o TEMPO ATÉ A REINCIDÊNCIA como um problema de
sobrevivência: Kaplan-Meier estratificado por faixa etária/sexo, e Cox
para identificar quais características da primeira internação predizem
maior risco de reincidência.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
import matplotlib.pyplot as plt

from pysus.online_data.SIH import download as download_sih

PREFIXOS_CAUSAS_EXTERNAS = ('V', 'W', 'X', 'Y')


def carregar_internacoes_causas_externas(uf: str, anos: list) -> pd.DataFrame:
    dfs = []
    for ano in anos:
        print(f"[LOG] Baixando SIH para {uf}/{ano}...")
        downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
        df_ano = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
        dfs.append(df_ano)
    df = pd.concat(dfs, ignore_index=True)
    df = df[df['DIAG_PRINC'].astype(str).str.upper().str.startswith(PREFIXOS_CAUSAS_EXTERNAS)].copy()
    return df


def construir_dataset_reincidencia(df: pd.DataFrame, data_fim_observacao: pd.Timestamp) -> pd.DataFrame:
    df['pseudo_id'] = df['NASC'].astype(str) + '_' + df['SEXO'].astype(str) + '_' + df['MUNIC_RES'].astype(str)
    df['DT_INTER'] = pd.to_datetime(df['DT_INTER'], format='%Y%m%d', errors='coerce')
    df = df.dropna(subset=['DT_INTER', 'pseudo_id'])
    df = df.sort_values(['pseudo_id', 'DT_INTER'])

    primeira_internacao = df.groupby('pseudo_id').first().reset_index()
    df['proxima_internacao'] = df.groupby('pseudo_id')['DT_INTER'].shift(-1)
    df['dias_ate_reincidencia'] = (df['proxima_internacao'] - df['DT_INTER']).dt.days

    primeiros = df.sort_values(['pseudo_id', 'DT_INTER']).drop_duplicates(subset=['pseudo_id'], keep='first').copy()
    primeiros['REINCIDIU'] = primeiros['dias_ate_reincidencia'].notna().astype(int)
    primeiros['dias_ate_censura'] = (data_fim_observacao - primeiros['DT_INTER']).dt.days
    primeiros['DURACAO_DIAS'] = primeiros['dias_ate_reincidencia'].fillna(primeiros['dias_ate_censura'])
    primeiros = primeiros[primeiros['DURACAO_DIAS'] > 0]

    for col in ['IDADE', 'DIAS_PERM']:
        if col in primeiros.columns:
            primeiros[col] = pd.to_numeric(primeiros[col], errors='coerce')
    primeiros['FAIXA_ETARIA'] = pd.cut(primeiros['IDADE'], bins=[0, 12, 19, 39, 59, 130],
                                        labels=['Criança (0-12)', 'Adolescente (13-19)', 'Adulto Jovem (20-39)', 'Adulto (40-59)', 'Idoso (60+)'])
    primeiros['CAPITULO_EXTERNA'] = primeiros['DIAG_PRINC'].astype(str).str[0]
    return primeiros


def analisar_kaplan_meier(df: pd.DataFrame, coluna_estrato: str, dir_saida: Path):
    kmf = KaplanMeierFitter()
    fig, ax = plt.subplots(figsize=(11, 7))
    for grupo, subdf in df.groupby(coluna_estrato, observed=True):
        if len(subdf) < 15:
            continue
        kmf.fit(subdf['DURACAO_DIAS'], subdf['REINCIDIU'], label=f"{grupo} (n={len(subdf)})")
        kmf.plot_survival_function(ax=ax)
    ax.set_title(f"Sobrevida Livre de Reincidência por Causa Externa, por {coluna_estrato}")
    ax.set_xlabel('Dias desde a primeira internação por causa externa')
    ax.set_ylabel('Probabilidade de ainda não ter reincidido')
    caminho_fig = dir_saida / f"kaplan_meier_reincidencia_por_{coluna_estrato.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Curva de Kaplan-Meier salva em: {caminho_fig}")


def analisar_cox(df: pd.DataFrame, dir_saida: Path):
    colunas = ['DURACAO_DIAS', 'REINCIDIU', 'IDADE', 'SEXO', 'DIAS_PERM', 'CAPITULO_EXTERNA']
    df_cox = df[[c for c in colunas if c in df.columns]].dropna(subset=['IDADE', 'DIAS_PERM']).copy()
    df_cox['SEXO'] = df_cox['SEXO'].astype(str)
    df_cox['CAPITULO_EXTERNA'] = df_cox['CAPITULO_EXTERNA'].astype(str)

    df_cox = pd.get_dummies(df_cox, columns=['SEXO', 'CAPITULO_EXTERNA'], drop_first=True, dtype=int)
    for col in list(df_cox.columns):
        if col not in ['DURACAO_DIAS', 'REINCIDIU'] and (df_cox[col].nunique() <= 1 or (df_cox[col].dtype == int and df_cox[col].sum() < 20)):
            df_cox = df_cox.drop(columns=[col])

    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_cox, duration_col='DURACAO_DIAS', event_col='REINCIDIU')

    print("\n" + "=" * 80)
    print("--- RESULTADO: FATORES DE RISCO PARA REINCIDÊNCIA POR CAUSA EXTERNA ---")
    print("=" * 80)
    print("(Hazard Ratio > 1 = reincide MAIS RÁPIDO/com maior risco)")
    cph.print_summary()

    fig, ax = plt.subplots(figsize=(10, 8))
    cph.plot(ax=ax)
    ax.set_title("Fatores de Risco para Reincidência por Causa Externa (Hazard Ratios)")
    caminho_fig = dir_saida / "cox_hazard_ratios_reincidencia.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de hazard ratios salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando internações por causa externa em {args.uf}/{args.anos} ---")
    df_raw = carregar_internacoes_causas_externas(args.uf, args.anos)
    print(f"✅ {len(df_raw)} internações por causa externa carregadas.")

    data_fim = pd.to_datetime(f"{max(args.anos)}-12-31")
    print(f"\n--- [ETAPA 2] Construindo dataset de reincidência (fim da observação: {data_fim.date()}) ---")
    df = construir_dataset_reincidencia(df_raw, data_fim)
    print(f"✅ {len(df)} pacientes com primeira internação identificada. Taxa de reincidência observada: {df['REINCIDIU'].mean():.1%}")

    if len(df) < 100:
        print("❌ Poucos pacientes para uma análise de sobrevida confiável (mínimo recomendado: 100).")
        return

    print(f"\n--- [ETAPA 3] Curva de Kaplan-Meier por faixa etária ---")
    analisar_kaplan_meier(df, 'FAIXA_ETARIA', dir_saida)

    print(f"\n--- [ETAPA 4] Ajustando modelo de Cox ---")
    analisar_cox(df, dir_saida)

    caminho_csv = dir_saida / f"reincidencia_causas_externas_{args.uf.lower()}.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Dados salvos em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE REINCIDÊNCIA POR CAUSA EXTERNA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise de sobrevida (Kaplan-Meier + Cox) do tempo até reincidência de internação por causa externa.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SIH a usar (recomenda-se >= 2 anos para observar reincidência).")
    parser.add_argument("--dir_saida", type=str, default="outputs/sobrevida_reincidencia_causas_externas", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
