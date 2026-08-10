# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE SOBREVIDA DO TEMPO DE PERMANÊNCIA HOSPITALAR (SIH)
======================================================================
Este script trata o tempo de internação (DIAS_PERM) como um problema de
Análise de Sobrevivência, em vez de uma simples média/mediana: o "evento"
de interesse é RECEBER ALTA COM VIDA, e a curva de Kaplan-Meier mostra a
probabilidade de UM PACIENTE AINDA ESTAR INTERNADO a cada dia — uma
visualização mais informativa do que a duração média para planejamento de
leitos. A Regressão de Cox quantifica quais fatores aceleram (hazard
ratio > 1) ou atrasam (hazard ratio < 1) a alta.

Limitação metodológica assumida (documentada explicitamente): óbitos
durante a internação são tratados como CENSURA (o paciente "sai" da
análise de tempo-até-alta-viva sem o evento de interesse ter ocorrido).
Isso é uma simplificação comum na literatura de tempo de permanência
quando não se aplica um modelo formal de riscos competitivos — o
correto, para uma análise mais rigorosa, seria uma abordagem de riscos
competitivos (alta vs. óbito), não implementada aqui.
"""

import argparse
from pathlib import Path

import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
import matplotlib.pyplot as plt

from pysus.online_data.SIH import download as download_sih


def carregar_internacoes(uf: str, anos: list, cid_prefixos: list) -> pd.DataFrame:
    dfs = []
    for ano in anos:
        print(f"[LOG] Baixando SIH para {uf}/{ano}...")
        downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
        df_ano = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
        dfs.append(df_ano)
    df = pd.concat(dfs, ignore_index=True)
    if cid_prefixos:
        df = df[df['DIAG_PRINC'].astype(str).str.startswith(tuple(cid_prefixos))]
    return df


def preparar_dados_sobrevida(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ['DIAS_PERM', 'MORTE', 'IDADE', 'SEXO', 'CAR_INT', 'UTI_MES_TO', 'DIAG_PRINC']
    df_modelo = df[[c for c in colunas if c in df.columns]].copy()

    for col in ['DIAS_PERM', 'IDADE', 'MORTE', 'UTI_MES_TO']:
        if col in df_modelo.columns:
            df_modelo[col] = pd.to_numeric(df_modelo[col], errors='coerce')

    df_modelo = df_modelo.dropna(subset=['DIAS_PERM', 'MORTE'])
    df_modelo = df_modelo[df_modelo['DIAS_PERM'] > 0]

    df_modelo['EVENTO_ALTA_VIVA'] = (df_modelo['MORTE'] == 0).astype(int)
    df_modelo['USOU_UTI'] = (df_modelo['UTI_MES_TO'].fillna(0) > 0).astype(int)
    if 'DIAG_PRINC' in df_modelo.columns:
        df_modelo['CAPITULO_CID'] = df_modelo['DIAG_PRINC'].astype(str).str[0]

    for col in ['SEXO', 'CAR_INT', 'CAPITULO_CID']:
        if col in df_modelo.columns:
            df_modelo[col] = df_modelo[col].astype(str)

    return df_modelo


def analisar_kaplan_meier(df: pd.DataFrame, dir_saida: Path):
    kmf = KaplanMeierFitter()
    fig, ax = plt.subplots(figsize=(11, 7))
    for usou_uti, subdf in df.groupby('USOU_UTI'):
        if len(subdf) < 10:
            continue
        rotulo = 'Usou UTI' if usou_uti == 1 else 'Não usou UTI'
        kmf.fit(subdf['DIAS_PERM'], subdf['EVENTO_ALTA_VIVA'], label=f"{rotulo} (n={len(subdf)})")
        kmf.plot_survival_function(ax=ax)
    ax.set_title("Curva de Kaplan-Meier — Tempo até Alta Viva, por Uso de UTI")
    ax.set_xlabel('Dias de internação')
    ax.set_ylabel('Probabilidade de ainda estar internado')
    caminho_fig = dir_saida / "kaplan_meier_permanencia_por_uti.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Curva de Kaplan-Meier salva em: {caminho_fig}")


def analisar_cox(df: pd.DataFrame, dir_saida: Path) -> CoxPHFitter:
    covariaveis_categoricas = [c for c in ['SEXO', 'CAR_INT', 'CAPITULO_CID'] if c in df.columns]
    colunas_modelo = ['DIAS_PERM', 'EVENTO_ALTA_VIVA', 'IDADE', 'USOU_UTI'] + covariaveis_categoricas
    df_cox = df[[c for c in colunas_modelo if c in df.columns]].dropna(subset=['IDADE']).copy()

    df_cox = pd.get_dummies(df_cox, columns=covariaveis_categoricas, drop_first=True, dtype=int)
    colunas_constantes = [c for c in df_cox.columns if c not in ['DIAS_PERM', 'EVENTO_ALTA_VIVA'] and df_cox[c].nunique() <= 1]
    df_cox = df_cox.drop(columns=colunas_constantes)

    # Remove categorias dummy muito raras para evitar instabilidade numérica no ajuste
    for col in df_cox.columns:
        if col not in ['DIAS_PERM', 'EVENTO_ALTA_VIVA', 'IDADE', 'USOU_UTI'] and df_cox[col].sum() < 30:
            df_cox = df_cox.drop(columns=[col])

    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_cox, duration_col='DIAS_PERM', event_col='EVENTO_ALTA_VIVA')

    print("\n" + "=" * 80)
    print("--- RESULTADO: MODELO DE COX PARA TEMPO ATÉ ALTA HOSPITALAR ---")
    print("=" * 80)
    print("(Hazard Ratio > 1 = recebe alta MAIS RÁPIDO; Hazard Ratio < 1 = permanece internado por MAIS TEMPO)")
    cph.print_summary()

    fig, ax = plt.subplots(figsize=(10, 8))
    cph.plot(ax=ax)
    ax.set_title("Fatores Associados ao Tempo de Permanência Hospitalar (Hazard Ratios)")
    caminho_fig = dir_saida / "cox_hazard_ratios_permanencia.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de hazard ratios salvo em: {caminho_fig}")
    return cph


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando internações para {args.uf}/{args.anos} ---")
    df_raw = carregar_internacoes(args.uf, args.anos, args.cids)
    print(f"✅ {len(df_raw)} internações carregadas.")

    print(f"\n--- [ETAPA 2] Preparando dados de sobrevida ---")
    df = preparar_dados_sobrevida(df_raw)
    print(f"✅ {len(df)} internações válidas. Taxa de óbito na amostra: {(1 - df['EVENTO_ALTA_VIVA']).mean():.1%}")

    if len(df) < 100:
        print("❌ Poucos casos para uma análise de sobrevida confiável (mínimo recomendado: 100).")
        return

    print(f"\n--- [ETAPA 3] Curva de Kaplan-Meier (Uso de UTI) ---")
    analisar_kaplan_meier(df, dir_saida)

    print(f"\n--- [ETAPA 4] Ajustando modelo de Cox ---")
    analisar_cox(df, dir_saida)

    caminho_csv = dir_saida / "dados_sobrevida_permanencia.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Dados de sobrevida salvos em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE SOBREVIDA DA PERMANÊNCIA HOSPITALAR CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise de sobrevida (Kaplan-Meier + Cox) do tempo de permanência hospitalar.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SIH a usar.")
    parser.add_argument("--cids", nargs="+", default=None, help="Prefixos de CID-10 para filtrar (opcional; se omitido, considera todas as internações).")
    parser.add_argument("--dir_saida", type=str, default="outputs/sobrevida_permanencia_hospitalar", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
