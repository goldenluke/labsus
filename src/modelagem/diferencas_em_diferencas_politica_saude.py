# -*- coding: utf-8 -*-
"""
======================================================================
  DIFERENÇAS-EM-DIFERENÇAS (DiD): IMPACTO DE UMA INTERVENÇÃO DE SAÚDE
======================================================================
Complementa o Pareamento por Escore de Propensão já usado em
`analise_impacto_causal.py` com outra técnica clássica de inferência
causal com dados observacionais: Diferenças-em-Diferenças. Em vez de
comparar indivíduos "parecidos", compara MUNICÍPIOS que receberam uma
intervenção (ex.: expansão de equipes de Saúde da Família, uma nova
política) contra municípios que não receberam, ANTES e DEPOIS da
intervenção — isolando o efeito da política da tendência geral que já
estava acontecendo em todos os municípios (o "contrafactual").

Efeito causal estimado = coeficiente da interação (Tratado × Período Pós).

Fonte: painel de indicadores multi-ano (gerado por integrar_indicadores.py).
"""

import argparse
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt


def carregar_painel(caminho_csv: Path, indicador: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_csv, sep=';', dtype={'cod_mun_ibge_6': str})
    if indicador not in df.columns:
        raise KeyError(f"Indicador '{indicador}' não encontrado no painel. Colunas disponíveis: {list(df.columns)}")
    return df[['cod_mun_ibge_6', 'UF', 'ANO', indicador]].dropna()


def preparar_dataset_did(df: pd.DataFrame, indicador: str, municipios_tratados: list, ano_intervencao: int) -> pd.DataFrame:
    df = df.copy()
    df['TRATADO'] = df['cod_mun_ibge_6'].isin(municipios_tratados).astype(int)
    df['POS_INTERVENCAO'] = (df['ANO'] >= ano_intervencao).astype(int)
    df['TRATADO_X_POS'] = df['TRATADO'] * df['POS_INTERVENCAO']
    df = df.rename(columns={indicador: 'Y'})
    return df


def verificar_tendencias_paralelas(df: pd.DataFrame, ano_intervencao: int, dir_saida: Path, indicador: str):
    """Gráfico de tendências pré-intervenção: se os grupos tratado/controle já
    caminhavam em paralelo antes da intervenção, a premissa central do DiD é
    mais defensável."""
    medias = df.groupby(['ANO', 'TRATADO'])['Y'].mean().reset_index()
    plt.figure(figsize=(11, 6))
    for tratado, sub in medias.groupby('TRATADO'):
        rotulo = 'Tratado' if tratado == 1 else 'Controle'
        plt.plot(sub['ANO'], sub['Y'], marker='o', label=rotulo)
    plt.axvline(ano_intervencao, color='red', linestyle='--', label=f'Intervenção ({ano_intervencao})')
    plt.title(f"Tendências: {indicador}, Tratado vs. Controle")
    plt.xlabel('Ano')
    plt.ylabel(indicador)
    plt.legend()
    caminho_fig = dir_saida / f"tendencias_did_{indicador.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de tendências salvo em: {caminho_fig}")


def ajustar_did(df: pd.DataFrame):
    modelo = smf.ols('Y ~ TRATADO + POS_INTERVENCAO + TRATADO_X_POS', data=df).fit(
        cov_type='cluster', cov_kwds={'groups': df['cod_mun_ibge_6']}
    )
    return modelo


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando painel de indicadores ('{args.indicador}') ---")
    df_painel = carregar_painel(Path(args.painel_csv), args.indicador)
    print(f"✅ {len(df_painel)} observações município-ano carregadas.")

    print(f"\n--- [ETAPA 2] Montando dataset DiD (tratamento: {len(args.municipios_tratados)} municípios, corte: {args.ano_intervencao}) ---")
    df = preparar_dataset_did(df_painel, args.indicador, args.municipios_tratados, args.ano_intervencao)
    n_tratados = df[df['TRATADO'] == 1]['cod_mun_ibge_6'].nunique()
    n_controle = df[df['TRATADO'] == 0]['cod_mun_ibge_6'].nunique()
    print(f"✅ {n_tratados} municípios tratados e {n_controle} municípios controle no painel.")

    if n_tratados == 0 or n_controle == 0:
        print("❌ É necessário ter ao menos um município tratado e um controle presentes no painel.")
        return

    verificar_tendencias_paralelas(df, args.ano_intervencao, dir_saida, args.indicador)

    print(f"\n--- [ETAPA 3] Ajustando o modelo de Diferenças-em-Diferenças ---")
    modelo = ajustar_did(df)

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: IMPACTO CAUSAL ESTIMADO SOBRE '{args.indicador}' ---")
    print("=" * 80)
    print(modelo.summary())

    efeito = modelo.params['TRATADO_X_POS']
    p_valor = modelo.pvalues['TRATADO_X_POS']
    ic = modelo.conf_int().loc['TRATADO_X_POS']
    print("\n--- INTERPRETAÇÃO ---")
    print(f"Efeito DiD (impacto causal estimado da intervenção): {efeito:+.4f}")
    print(f"Intervalo de confiança 95%: [{ic[0]:+.4f}, {ic[1]:+.4f}]")
    print(f"p-valor: {p_valor:.4f}")
    if p_valor < 0.05:
        direcao = "reduziu" if efeito < 0 else "aumentou"
        print(f"✅ A intervenção teve um efeito estatisticamente significante: {direcao} '{args.indicador}' em {abs(efeito):.4f} unidades, em média, nos municípios tratados.")
    else:
        print("⚠️ Não há evidência estatística de efeito causal significante da intervenção neste indicador.")
    print("=" * 80)

    resumo = pd.DataFrame([{
        'INDICADOR': args.indicador, 'ANO_INTERVENCAO': args.ano_intervencao,
        'N_MUNICIPIOS_TRATADOS': n_tratados, 'N_MUNICIPIOS_CONTROLE': n_controle,
        'EFEITO_DID': efeito, 'IC95_INFERIOR': ic[0], 'IC95_SUPERIOR': ic[1], 'P_VALOR': p_valor,
    }])
    caminho_csv = dir_saida / f"resultado_did_{args.indicador.lower()}.csv"
    resumo.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resumo salvo em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE DIFERENÇAS-EM-DIFERENÇAS CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estima o impacto causal de uma intervenção via Diferenças-em-Diferenças.")
    parser.add_argument("--painel-csv", type=str, required=True, help="Caminho para o painel de indicadores multi-ano (gerado por integrar_indicadores.py).")
    parser.add_argument("--indicador", type=str, required=True, help="Coluna de indicador a usar como desfecho (ex: TMI, TAXA_INTERNACAO_GERAL).")
    parser.add_argument("--municipios-tratados", nargs="+", required=True, help="Lista de códigos IBGE (6 dígitos) dos municípios que receberam a intervenção.")
    parser.add_argument("--ano-intervencao", type=int, required=True, help="Ano em que a intervenção começou (primeiro ano do período 'pós').")
    parser.add_argument("--dir_saida", type=str, default="outputs/diferencas_em_diferencas", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
