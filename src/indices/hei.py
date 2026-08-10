# -*- coding: utf-8 -*-
"""
======================================================================
  HEALTHCARE EQUITY INDEX (HEI)
======================================================================
Objetivo: mensurar a desigualdade de acesso aos recursos do SUS ENTRE
os municípios de uma mesma UF/ano — diferente dos demais índices deste
módulo, o HEI não é uma propriedade de um único município, e sim da
DISTRIBUIÇÃO de recursos entre todos os municípios da UF: por isso o
mesmo valor é atribuído a todos os municípios daquele UF/ano (é a forma
de encaixar uma estatística de nível estadual no esquema de junção por
cod_mun_ibge_6/ANO/UF usado pela pipeline de Integração de Indicadores).

Indicadores usados (src/features/):
  - capacidade_assistencial: TAXA_LEITOS_MIL, TAXA_MEDICOS_MIL_CAP,
    TAXA_ENFERMEIROS_MIL, TAXA_EQUIPES_ESF_DEZ_MIL — a distribuição
    desses recursos por habitante entre os municípios é o insumo dos
    quatro índices de desigualdade abaixo.

Métricas (src/utils/indices_compostos.py):
  - Gini, Theil, Hoover — calculados sobre CADA recurso separadamente
    e depois combinados numa média simples (todos em escalas comparáveis:
    Gini/Hoover em [0,1], Theil não-negativo).
  - Palma — razão do decil mais rico sobre os 4 decis mais pobres,
    calculada sobre o índice de capacidade assistencial agregado (não
    tem sentido comparável entre as quatro variáveis brutas ao mesmo
    tempo, então usamos a versão já combinada em capacidade_assistencial).

HEI_GINI/THEIL/HOOVER/PALMA_RECURSOS_SAUDE ficam altos quando os
recursos de saúde estão concentrados em poucos municípios da UF
(tipicamente a capital/polos regionais) e baixos quando distribuídos de
forma mais equitativa entre os municípios.
"""
import pandas as pd

from ..features import capacidade_assistencial
from ..utils.indices_compostos import indice_gini, indice_theil, indice_hoover, indice_palma

CHAVES = ['cod_mun_ibge_6', 'ANO', 'UF']
RECURSOS = ['TAXA_LEITOS_MIL', 'TAXA_MEDICOS_MIL_CAP', 'TAXA_ENFERMEIROS_MIL', 'TAXA_EQUIPES_ESF_DEZ_MIL']


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    print("\n=== Calculando HEI: chamando indicador de capacidade assistencial ===")

    df_cap = capacidade_assistencial.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    if df_cap.empty:
        print("⚠️ Nenhum dado disponível para calcular o HEI.")
        return pd.DataFrame()

    df = df_cap[CHAVES + ['municipio', 'populacao'] + RECURSOS + ['IND_CAPACIDADE_ASSISTENCIAL']].copy()

    linhas_uf_ano = []
    for (uf, ano), grupo in df.groupby(['UF', 'ANO']):
        ginis = [indice_gini(grupo[col]) for col in RECURSOS]
        theils = [indice_theil(grupo[col]) for col in RECURSOS]
        hoovers = [indice_hoover(grupo[col]) for col in RECURSOS]
        linhas_uf_ano.append({
            'UF': uf, 'ANO': ano,
            'GINI_RECURSOS_SAUDE': sum(ginis) / len(ginis),
            'THEIL_RECURSOS_SAUDE': sum(theils) / len(theils),
            'HOOVER_RECURSOS_SAUDE': sum(hoovers) / len(hoovers),
            'PALMA_RECURSOS_SAUDE': indice_palma(grupo['IND_CAPACIDADE_ASSISTENCIAL']),
        })
    df_desigualdade_uf = pd.DataFrame(linhas_uf_ano)

    df = df.merge(df_desigualdade_uf, on=['UF', 'ANO'], how='left')
    df['HEI'] = 100 * (
        df['GINI_RECURSOS_SAUDE'].fillna(0) + df['HOOVER_RECURSOS_SAUDE'].fillna(0)
    ) / 2

    # Descarta os componentes brutos emprestados e renomeia as métricas de
    # desigualdade com o sufixo _HEI: a pipeline de Integração de Indicadores
    # mescla todas as colunas maiúsculas de todos os índices selecionados —
    # nomes sem sufixo colidiriam se outro índice reexportar o mesmo
    # indicador de base ou reusar um nome de métrica genérico.
    df = df.rename(columns={
        'GINI_RECURSOS_SAUDE': 'GINI_RECURSOS_SAUDE_HEI',
        'THEIL_RECURSOS_SAUDE': 'THEIL_RECURSOS_SAUDE_HEI',
        'HOOVER_RECURSOS_SAUDE': 'HOOVER_RECURSOS_SAUDE_HEI',
        'PALMA_RECURSOS_SAUDE': 'PALMA_RECURSOS_SAUDE_HEI',
    })
    df = df.drop(columns=RECURSOS + ['IND_CAPACIDADE_ASSISTENCIAL'])

    print("✅ HEI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Healthcare Equity Index (HEI) por UF/ano.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "hei.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
