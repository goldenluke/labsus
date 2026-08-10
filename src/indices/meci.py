# -*- coding: utf-8 -*-
"""
======================================================================
  MUNICIPAL EPIDEMIOLOGICAL COMPLEXITY INDEX (MECI)
======================================================================
Objetivo: mensurar a complexidade epidemiológica de um município —
o quão diversificada é a carga de doenças e a produção assistencial
que ele processa, em vez de concentrada num pequeno número de causas.

Indicadores usados (nenhum dado bruto do DATASUS é tocado aqui — este
módulo só chama e combina indicadores de src/features/):
  - diversidade_epidemiologica.SHANNON_DIVERSIDADE_OBITOS (SIM)
  - diversidade_epidemiologica.SHANNON_DIVERSIDADE_INTERNACOES (SIH)
  - complexidade_hospitalar.N_PROC_DISTINTOS_HOSP (SIH, proxy p/ diversidade
    de procedimentos — não há um indicador de "diversidade ambulatorial"
    do SIA em features/ ainda, então este componente cobre parcialmente
    esse eixo do MECI original)
  - diversidade_assistencial.SHANNON_DIVERSIDADE_ASSISTENCIAL (CNES, proxy
    p/ diversidade de especialidades — usa tipos de estabelecimento, não
    o cadastro de especialidades do CNES/SR, que não está coberto ainda)

Método: cada componente já é comparável entre si (bits de Shannon ou
contagem), então o MECI é a 1ª componente principal (PCA) dos quatro,
reescalada para 0-100 — mesma abordagem de combinar_indice_composto()
usada nos índices de 1ª camada.
"""
import pandas as pd

from ..features import diversidade_epidemiologica, complexidade_hospitalar, diversidade_assistencial
from ..utils.indices_compostos import combinar_indice_composto

CHAVES = ['cod_mun_ibge_6', 'ANO', 'UF']


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    print("\n=== Calculando MECI: chamando indicadores de diversidade/complexidade ===")

    df_epi = diversidade_epidemiologica.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_hosp = complexidade_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_ass = diversidade_assistencial.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)

    if df_epi.empty:
        print("⚠️ Nenhum dado disponível para calcular o MECI.")
        return pd.DataFrame()

    df = df_epi[CHAVES + ['municipio', 'populacao', 'SHANNON_DIVERSIDADE_OBITOS', 'SHANNON_DIVERSIDADE_INTERNACOES']].copy()
    df = df.merge(df_hosp[CHAVES + ['N_PROC_DISTINTOS_HOSP']], on=CHAVES, how='left')
    df = df.merge(df_ass[CHAVES + ['SHANNON_DIVERSIDADE_ASSISTENCIAL']], on=CHAVES, how='left')

    # Renomeia os componentes emprestados com o sufixo _MECI: mais de um
    # índice pode importar o mesmo indicador de base (ex.: outro índice
    # também usa SHANNON_DIVERSIDADE_OBITOS), e a pipeline de Integração de
    # Indicadores mescla TODAS as colunas maiúsculas de TODOS os índices
    # selecionados — nomes sem sufixo colidiriam entre índices diferentes.
    df = df.rename(columns={
        'SHANNON_DIVERSIDADE_OBITOS': 'SHANNON_DIVERSIDADE_OBITOS_MECI',
        'SHANNON_DIVERSIDADE_INTERNACOES': 'SHANNON_DIVERSIDADE_INTERNACOES_MECI',
        'N_PROC_DISTINTOS_HOSP': 'N_PROC_DISTINTOS_HOSP_MECI',
        'SHANNON_DIVERSIDADE_ASSISTENCIAL': 'SHANNON_DIVERSIDADE_ASSISTENCIAL_MECI',
    })
    colunas_componentes = [
        'SHANNON_DIVERSIDADE_OBITOS_MECI', 'SHANNON_DIVERSIDADE_INTERNACOES_MECI',
        'N_PROC_DISTINTOS_HOSP_MECI', 'SHANNON_DIVERSIDADE_ASSISTENCIAL_MECI',
    ]
    df[colunas_componentes] = df[colunas_componentes].fillna(0)

    df['MECI'] = combinar_indice_composto(df, colunas_componentes)

    print("✅ MECI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Municipal Epidemiological Complexity Index (MECI).")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "meci.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
