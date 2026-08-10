# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE SOBREVIDA DO TRATAMENTO DE TUBERCULOSE (SINAN/TUBE)
======================================================================
Complementa o modelo de classificação de risco de abandono
(`modelo_risco_abandono_tb.py`, que prevê SE o paciente vai abandonar)
com a pergunta "QUANDO": este script trata o tempo entre o diagnóstico
e o encerramento do caso como um problema de Análise de Sobrevivência —
Kaplan-Meier para visualizar a curva de "permanência em tratamento" por
subgrupo, e Regressão de Cox para quantificar quais fatores aceleram o
abandono (hazard ratio > 1) ou a cura.

O desfecho "abandono" é tratado como o EVENTO de interesse; "cura" e
demais desfechos são tratados como CENSURA (o paciente "saiu" da análise
de risco de abandono por um motivo diferente do evento estudado).
"""

import argparse
from pathlib import Path

import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
import matplotlib.pyplot as plt

from pysus.online_data.SINAN import SINAN


def carregar_dados_tb(anos: list) -> pd.DataFrame:
    sinan_db = SINAN().load()
    files = sinan_db.get_files(dis_code='TUBE', year=anos)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo SINAN/TUBE encontrado para {anos}.")
    downloaded = sinan_db.download(files)
    df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    return df


def preparar_dados_sobrevida(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a duração (dias entre diagnóstico e encerramento) e o indicador
    de evento (1 = abandono, 0 = censurado, incluindo cura)."""
    colunas_data = [c for c in ['DT_DIAG', 'DT_NOTIFIC'] if c in df.columns]
    if not colunas_data:
        raise KeyError("Nenhuma coluna de data de início (DT_DIAG/DT_NOTIFIC) encontrada.")
    col_inicio = colunas_data[0]

    if 'DT_ENCERRA' not in df.columns:
        raise KeyError("Coluna 'DT_ENCERRA' (data de encerramento do caso) não encontrada nos dados do SINAN/TUBE.")

    df[col_inicio] = pd.to_datetime(df[col_inicio], errors='coerce')
    df['DT_ENCERRA'] = pd.to_datetime(df['DT_ENCERRA'], errors='coerce')
    df['SITUA_ENCE'] = pd.to_numeric(df['SITUA_ENCE'], errors='coerce')

    df = df[df['SITUA_ENCE'].isin([1, 2, 3])].copy()  # 1=Cura, 2=Abandono, 3=Óbito (por TB ou outras causas)
    df['DURACAO_DIAS'] = (df['DT_ENCERRA'] - df[col_inicio]).dt.days
    df = df[(df['DURACAO_DIAS'] > 0) & (df['DURACAO_DIAS'] < 3650)]  # remove datas inconsistentes (>10 anos)
    df['EVENTO_ABANDONO'] = (df['SITUA_ENCE'] == 2).astype(int)

    covariaveis = ['NU_IDADE_N', 'CS_SEXO', 'CS_RACA', 'CS_ESCOL_N', 'AGRA_ALCOO', 'AGRA_DIABE', 'AGRA_HIV', 'AGRA_TABAC', 'TRAT_SUPER']
    covariaveis_existentes = [c for c in covariaveis if c in df.columns]

    df_final = df[['DURACAO_DIAS', 'EVENTO_ABANDONO'] + covariaveis_existentes].copy()
    if 'NU_IDADE_N' in df_final.columns:
        df_final['NU_IDADE_N'] = df_final['NU_IDADE_N'].astype(str)
        mascara_idade_valida = (df_final['NU_IDADE_N'].str.len() == 4) & (df_final['NU_IDADE_N'].str.startswith('4'))
        df_final['IDADE'] = pd.to_numeric(df_final['NU_IDADE_N'].str[1:], errors='coerce')
        df_final = df_final[mascara_idade_valida & df_final['IDADE'].notna()]
        df_final = df_final.drop(columns=['NU_IDADE_N'])
        covariaveis_existentes = [c for c in covariaveis_existentes if c != 'NU_IDADE_N'] + ['IDADE']

    for col in [c for c in covariaveis_existentes if c != 'IDADE']:
        df_final[col] = df_final[col].astype(str)

    df_final = df_final.dropna(subset=['DURACAO_DIAS', 'EVENTO_ABANDONO'])
    return df_final, covariaveis_existentes


def analisar_kaplan_meier(df: pd.DataFrame, coluna_estrato: str, dir_saida: Path):
    kmf = KaplanMeierFitter()
    fig, ax = plt.subplots(figsize=(11, 7))
    for grupo, subdf in df.groupby(coluna_estrato):
        if len(subdf) < 10:
            continue
        kmf.fit(subdf['DURACAO_DIAS'], subdf['EVENTO_ABANDONO'], label=f"{coluna_estrato}={grupo} (n={len(subdf)})")
        kmf.plot_survival_function(ax=ax)
    ax.set_title(f"Curva de Kaplan-Meier — Permanência em Tratamento (livre de abandono) por {coluna_estrato}")
    ax.set_xlabel('Dias desde o diagnóstico')
    ax.set_ylabel('Probabilidade de ainda estar em tratamento (sem abandono)')
    caminho_fig = dir_saida / f"kaplan_meier_tb_por_{coluna_estrato.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Curva de Kaplan-Meier salva em: {caminho_fig}")


def analisar_cox(df: pd.DataFrame, covariaveis: list, dir_saida: Path):
    df_cox = df.copy()
    cols_categoricas = [c for c in covariaveis if c != 'IDADE']
    df_cox = pd.get_dummies(df_cox, columns=cols_categoricas, drop_first=True, dtype=int)

    colunas_constantes = [c for c in df_cox.columns if c not in ['DURACAO_DIAS', 'EVENTO_ABANDONO'] and df_cox[c].nunique() <= 1]
    df_cox = df_cox.drop(columns=colunas_constantes)

    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_cox, duration_col='DURACAO_DIAS', event_col='EVENTO_ABANDONO')

    print("\n" + "=" * 80)
    print("--- RESULTADO: MODELO DE COX PARA RISCO DE ABANDONO DO TRATAMENTO DE TB ---")
    print("=" * 80)
    cph.print_summary()

    fig, ax = plt.subplots(figsize=(10, 8))
    cph.plot(ax=ax)
    ax.set_title("Fatores de Risco para Abandono do Tratamento de TB (Hazard Ratios, log-escala)")
    caminho_fig = dir_saida / "cox_hazard_ratios_tb.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de hazard ratios salvo em: {caminho_fig}")

    return cph


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando dados do SINAN/TUBE para {args.anos} ---")
    df_raw = carregar_dados_tb(args.anos)
    print(f"✅ {len(df_raw)} notificações carregadas.")

    print(f"\n--- [ETAPA 2] Preparando dados de sobrevida (duração + evento) ---")
    df, covariaveis = preparar_dados_sobrevida(df_raw)
    print(f"✅ {len(df)} casos válidos com desfecho e duração consistentes.")
    print(f"Taxa de abandono na amostra: {df['EVENTO_ABANDONO'].mean():.1%}")

    if len(df) < 50:
        print("❌ Poucos casos para uma análise de sobrevida confiável (mínimo recomendado: 50).")
        return

    print(f"\n--- [ETAPA 3] Curvas de Kaplan-Meier por '{args.estrato}' ---")
    if args.estrato in df.columns:
        analisar_kaplan_meier(df, args.estrato, dir_saida)
    else:
        print(f"⚠️ Coluna '{args.estrato}' não disponível nos dados. Pulando Kaplan-Meier estratificado.")

    print(f"\n--- [ETAPA 4] Ajustando modelo de Cox ---")
    analisar_cox(df, covariaveis, dir_saida)

    caminho_csv = dir_saida / "dados_sobrevida_tb.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Dados de sobrevida salvos em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE SOBREVIDA DO TRATAMENTO DE TB CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise de sobrevida (Kaplan-Meier + Cox) do tempo até abandono do tratamento de TB.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022, 2023], help="Anos de dados do SINAN-TB a usar.")
    parser.add_argument("--estrato", type=str, default="CS_SEXO", help="Coluna categórica para estratificar a curva de Kaplan-Meier (ex: CS_SEXO, TRAT_SUPER).")
    parser.add_argument("--dir_saida", type=str, default="outputs/sobrevida_tratamento_tb", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
