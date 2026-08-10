# -*- coding: utf-8 -*-
"""
======================================================================
  CLASSIFICAÇÃO DE ROBSON (10 GRUPOS) E AUDITORIA DE CESARIANAS (SINASC)
======================================================================
Implementa a Classificação de Robson — a ferramenta padrão-ouro
recomendada pela OMS para monitorar e comparar taxas de cesárea entre
maternidades/regiões/países, dividindo TODOS os partos em 10 grupos
mutuamente exclusivos e coletivamente exaustivos, com base em 5
características obstétricas objetivas disponíveis no SINASC: paridade,
cesárea prévia, número de fetos, apresentação fetal, idade gestacional
e tipo de início do trabalho de parto (ver Apêndice C do dicionário de
dados do projeto, com as tabelas oficiais de critérios).

O relatório de Robson responde duas perguntas centrais de auditoria
obstétrica: (1) qual grupo mais CONTRIBUI para a taxa geral de cesárea
de uma região/hospital? (2) o Grupo 1 e 3 (nulíparas/multíparas de baixo
risco, trabalho de parto espontâneo — a OMS considera esse o alvo
prioritário de melhoria) têm taxa de cesárea anormalmente alta em algum
hospital específico?
"""

import argparse
from pathlib import Path

import pandas as pd

from pysus.online_data.SINASC import download as download_sinasc


def carregar_nascimentos(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
    downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
    df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    return df


def classificar_robson(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ['QTDPARTNOR', 'QTDPARTCES', 'GRAVIDEZ', 'TPAPRESENT', 'GESTACAO', 'STTRABPART', 'STCESPARTO', 'PARTO']:
        if col not in df.columns:
            raise KeyError(f"Coluna '{col}' (necessária para a Classificação de Robson) não encontrada no SINASC.")
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=['QTDPARTNOR', 'QTDPARTCES', 'GRAVIDEZ', 'TPAPRESENT', 'GESTACAO'])

    nulipara = (df['QTDPARTNOR'].fillna(0) + df['QTDPARTCES'].fillna(0)) == 0
    cesarea_previa = df['QTDPARTCES'].fillna(0) > 0
    unico = df['GRAVIDEZ'] == 1
    cefalica = df['TPAPRESENT'] == 1
    pelvica = df['TPAPRESENT'] == 2
    transversa = df['TPAPRESENT'] == 3
    a_termo = df['GESTACAO'].isin([5, 6])
    pre_termo = df['GESTACAO'].isin([1, 2, 3, 4])
    tp_espontaneo = (df['STTRABPART'] == 2) & (df['STCESPARTO'] != 1)
    tp_induzido_ou_cesarea_previa_ao_tp = (df['STTRABPART'] == 1) | (df['STCESPARTO'] == 1)

    grupo = pd.Series(0, index=df.index, dtype=int)  # 0 = não classificado

    grupo = grupo.where(~(unico & transversa), 9)
    grupo = grupo.where(~(df['GRAVIDEZ'].isin([2, 3])), 8)
    grupo = grupo.where(~(unico & pelvica & nulipara & (grupo == 0)), 6)
    grupo = grupo.where(~(unico & pelvica & ~nulipara & (grupo == 0)), 7)
    grupo = grupo.where(~(unico & cefalica & pre_termo & (grupo == 0)), 10)
    grupo = grupo.where(~(unico & cefalica & a_termo & nulipara & tp_espontaneo & (grupo == 0)), 1)
    grupo = grupo.where(~(unico & cefalica & a_termo & nulipara & tp_induzido_ou_cesarea_previa_ao_tp & (grupo == 0)), 2)
    grupo = grupo.where(~(unico & cefalica & a_termo & ~nulipara & ~cesarea_previa & tp_espontaneo & (grupo == 0)), 3)
    grupo = grupo.where(~(unico & cefalica & a_termo & ~nulipara & ~cesarea_previa & tp_induzido_ou_cesarea_previa_ao_tp & (grupo == 0)), 4)
    grupo = grupo.where(~(unico & cefalica & a_termo & ~nulipara & cesarea_previa & (grupo == 0)), 5)

    df['GRUPO_ROBSON'] = grupo
    df['FOI_CESAREA'] = (df['PARTO'] == 2).astype(int)
    df = df[df['GRUPO_ROBSON'] > 0]  # remove os poucos casos com combinação de dados inconsistente/incompleta
    return df


def gerar_relatorio_robson(df: pd.DataFrame) -> pd.DataFrame:
    total_nascimentos = len(df)
    total_cesareas = df['FOI_CESAREA'].sum()

    relatorio = df.groupby('GRUPO_ROBSON').agg(
        N_PARTOS=('FOI_CESAREA', 'size'),
        N_CESAREAS=('FOI_CESAREA', 'sum'),
    ).reset_index()
    relatorio['PERC_DO_TOTAL_DE_PARTOS'] = (relatorio['N_PARTOS'] / total_nascimentos) * 100
    relatorio['TAXA_CESAREA_NO_GRUPO'] = (relatorio['N_CESAREAS'] / relatorio['N_PARTOS']) * 100
    relatorio['PERC_CONTRIBUICAO_TAXA_CESAREA_GERAL'] = (relatorio['N_CESAREAS'] / total_cesareas) * 100
    relatorio = relatorio.sort_values('GRUPO_ROBSON')
    return relatorio


def auditar_hospitais_grupo_baixo_risco(df: pd.DataFrame, min_partos_hospital: int) -> pd.DataFrame:
    """Foca nos Grupos 1 e 3 (nulípara/multípara de baixo risco, trabalho de
    parto espontâneo) — o alvo prioritário da OMS para redução de cesáreas
    desnecessárias — e ranqueia hospitais pela taxa de cesárea NESSE grupo."""
    if 'CODESTAB' not in df.columns:
        return pd.DataFrame()
    df_baixo_risco = df[df['GRUPO_ROBSON'].isin([1, 3])]
    por_hospital = df_baixo_risco.groupby('CODESTAB').agg(
        N_PARTOS_BAIXO_RISCO=('FOI_CESAREA', 'size'),
        N_CESAREAS_BAIXO_RISCO=('FOI_CESAREA', 'sum'),
    ).reset_index()
    por_hospital = por_hospital[por_hospital['N_PARTOS_BAIXO_RISCO'] >= min_partos_hospital]
    por_hospital['TAXA_CESAREA_BAIXO_RISCO'] = (por_hospital['N_CESAREAS_BAIXO_RISCO'] / por_hospital['N_PARTOS_BAIXO_RISCO']) * 100
    return por_hospital.sort_values('TAXA_CESAREA_BAIXO_RISCO', ascending=False)


def gerar_grafico(relatorio: pd.DataFrame, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.bar(relatorio['GRUPO_ROBSON'].astype(str), relatorio['PERC_DO_TOTAL_DE_PARTOS'], color='#4575b4', alpha=0.7, label='% do total de partos')
    ax1.set_xlabel('Grupo de Robson')
    ax1.set_ylabel('% do total de partos', color='#4575b4')
    ax2 = ax1.twinx()
    ax2.plot(relatorio['GRUPO_ROBSON'].astype(str), relatorio['TAXA_CESAREA_NO_GRUPO'], color='#d73027', marker='o', linewidth=2, label='Taxa de cesárea no grupo (%)')
    ax2.set_ylabel('Taxa de cesárea no grupo (%)', color='#d73027')
    plt.title(f'Classificação de Robson (10 Grupos) — {uf}')
    fig.tight_layout()
    caminho_fig = dir_saida / f"classificacao_robson_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando nascimentos para {args.uf}/{args.ano} ---")
    df_raw = carregar_nascimentos(args.uf, args.ano)
    print(f"✅ {len(df_raw)} nascimentos carregados.")

    print(f"\n--- [ETAPA 2] Aplicando a Classificação de Robson (10 grupos) ---")
    df = classificar_robson(df_raw)
    print(f"✅ {len(df)} partos classificados com sucesso.")

    if len(df) < 50:
        print("❌ Poucos partos para um relatório de Robson confiável (mínimo recomendado: 50).")
        return

    print(f"\n--- [ETAPA 3] Gerando o Relatório de Robson ---")
    relatorio = gerar_relatorio_robson(df)

    print("\n" + "=" * 90)
    print(f"--- RELATÓRIO DE ROBSON — {args.uf}/{args.ano} ---")
    print("=" * 90)
    print(f"Taxa de cesárea geral: {df['FOI_CESAREA'].mean():.1%}")
    print(relatorio.round(2).to_string(index=False))
    grupo_maior_contribuicao = relatorio.sort_values('PERC_CONTRIBUICAO_TAXA_CESAREA_GERAL', ascending=False).iloc[0]
    print(f"\n➡️ Grupo que mais CONTRIBUI para a taxa geral de cesárea: Grupo {int(grupo_maior_contribuicao['GRUPO_ROBSON'])} "
          f"({grupo_maior_contribuicao['PERC_CONTRIBUICAO_TAXA_CESAREA_GERAL']:.1f}% de todas as cesáreas).")
    print("=" * 90)

    caminho_csv = dir_saida / f"relatorio_robson_{args.uf.lower()}_{args.ano}.csv"
    relatorio.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Relatório de Robson salvo em: '{caminho_csv}'")

    gerar_grafico(relatorio, args.uf, dir_saida)

    print(f"\n--- [ETAPA 4] Auditando hospitais pela taxa de cesárea nos Grupos 1 e 3 (baixo risco) ---")
    auditoria = auditar_hospitais_grupo_baixo_risco(df, args.min_partos_hospital)
    if not auditoria.empty:
        print(f"✅ {len(auditoria)} hospitais com volume suficiente para auditoria.")
        print("\nTop 10 hospitais com MAIOR taxa de cesárea em partos de baixo risco (Grupos 1+3):")
        print(auditoria.head(10).round(1).to_string(index=False))
        caminho_auditoria = dir_saida / f"auditoria_hospitais_baixo_risco_{args.uf.lower()}_{args.ano}.csv"
        auditoria.to_csv(caminho_auditoria, index=False, sep=';', encoding='utf-8-sig')
        print(f"📄 Auditoria por hospital salva em: '{caminho_auditoria}'")
    else:
        print("⚠️ Coluna de estabelecimento (CODESTAB) não disponível ou nenhum hospital com volume suficiente.")

    print("\n" + "=" * 80)
    print("🎉 CLASSIFICAÇÃO DE ROBSON E AUDITORIA DE CESARIANAS CONCLUÍDAS! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classifica partos pela Classificação de Robson (10 grupos) e audita taxas de cesárea.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--min-partos-hospital", type=int, default=20, help="Nº mínimo de partos de baixo risco (Grupos 1+3) para um hospital entrar na auditoria.")
    parser.add_argument("--dir_saida", type=str, default="outputs/classificacao_robson", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
