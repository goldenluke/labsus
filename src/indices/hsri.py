# -*- coding: utf-8 -*-
"""
======================================================================
  HEALTHCARE STRUCTURAL ROBUSTNESS INDEX (HSRI) — nome revisado, sigla mantida
======================================================================
Objetivo: mensurar o equilíbrio entre capacidade instalada, pressão
assistencial (demanda) e mortalidade hospitalar de um sistema de saúde
municipal, num único ponto no tempo.

Nome revisado (era "Healthcare System Resilience Index"): resiliência,
na literatura de sistemas complexos e de saúde, é uma propriedade
DINÂMICA — capacidade de manter desempenho DEPOIS de um choque (antes →
choque → depois; ou Δdesempenho/Δdemanda). Este índice não tem
componente temporal: ele descreve um ESTADO (quanta capacidade um
município tem frente à demanda/mortalidade que já enfrenta), não uma
resposta a uma perturbação. Um município com Capacidade=90/Demanda=80/
Mortalidade=5 pode ser, na prática, mais robusto que um com
Capacidade=90/Demanda=10/Mortalidade=5 (absorve 8x mais demanda com a
mesma mortalidade) — mas a fórmula pontua o segundo bem mais alto,
porque mede robustez estrutural, não resposta a estresse. Medir
resiliência de verdade exigiria uma série temporal com um choque
identificável (ex.: elasticidade Δmortalidade/Δdemanda entre dois
períodos), o que está fora do escopo deste módulo. A sigla HSRI é
mantida — H-S-R-I ainda bate letra a letra com "Healthcare Structural
Robustness Index" — para não quebrar integrações existentes (coluna de
saída, FileType do Django, chave no frontend).

Indicadores usados (src/features/ — nenhum dado bruto tocado aqui):
  - capacidade_assistencial.IND_CAPACIDADE_ASSISTENCIAL  → Capacidade
  - complexidade_hospitalar.N_INTERNACOES_HOSP,
    complexidade_hospitalar.IND_COMPLEXIDADE_HOSPITALAR  → Demanda
  - pressao_hospitalar.IND_PRESSAO_PERMANENCIA            → Demanda
  - mortalidade_hospitalar_ajustada.TMH_HOSPITALAR        → Mortalidade

A Mortalidade usa só a mortalidade HOSPITALAR ajustada (a mortalidade
GERAL do município foi removida): mortalidade geral mistura dezenas de
fatores sem relação com desempenho hospitalar (envelhecimento,
violência, suicídio, câncer, acidentes, perfil demográfico) e só
adicionava ruído ao componente, sem melhorar o que o índice tenta medir.

Fórmula:

                Capacidade
    ─────────────────────────────────────
    1 + 0.5 × Demanda + 0.5 × Mortalidade

Capacidade, Demanda e Mortalidade são, cada uma, um índice 0-100 (PCA
dos componentes listados acima). A combinação de Demanda e Mortalidade é
ADITIVA, não multiplicativa (a versão original fazia Demanda × Mortalidade):
multiplicar as duas faz a razão explodir de forma extrema para pequenas
variações — D=M=80 dá produto 6.400, enquanto D=M=40 (metade da pressão
em cada eixo) dá 1.600, 4x menor, uma sensibilidade desproporcional. A
regularização (+1) fica só no denominador, sem somar 1 também ao
numerador (que alteraria também municípios sem capacidade nenhuma, sem
necessidade).

A razão final vira 0-100 por uma função LOGÍSTICA de parâmetros FIXOS
sobre log(razão) — não por min-max do lote atual. Min-max faz HSRI=80
incomparável entre execuções: a mesma razão bruta recebe pontuações
diferentes dependendo de quais outros municípios entraram no mesmo lote
de UFs/anos. A escala logística fixa sempre mapeia razão=1 (capacidade
== pressão) para score=50, independente do lote — mais comparável entre
UFs e anos. Limitação que isso NÃO resolve, documentada por
transparência: Capacidade/Demanda/Mortalidade continuam, elas mesmas,
reescalados 0-100 por lote dentro de `combinar_indice_composto` — uma
característica compartilhada por todos os índices de 2ª camada desta
base de código, não corrigida aqui.
"""
import numpy as np
import pandas as pd

from ..features import capacidade_assistencial, complexidade_hospitalar, pressao_hospitalar, mortalidade_hospitalar_ajustada
from ..utils.indices_compostos import combinar_indice_composto

CHAVES = ['cod_mun_ibge_6', 'ANO', 'UF']

PESO_DEMANDA_HSRI = 0.5
PESO_MORTALIDADE_HSRI = 0.5
INCLINACAO_LOGISTICA_HSRI = 1.5  # quanto maior, mais rápido o score satura perto de 0/100 conforme a razão se afasta de 1


def _escala_fixa_logistica(razao: pd.Series, inclinacao: float = INCLINACAO_LOGISTICA_HSRI) -> pd.Series:
    """Converte a razão Capacidade/Pressão para 0-100 com parâmetros FIXOS
    (independentes do lote de municípios processado) — ver docstring do
    módulo. razao=1 (capacidade == pressão) sempre vira score=50."""
    log_razao = np.log(razao.clip(lower=1e-9))
    return 100 / (1 + np.exp(-inclinacao * log_razao))


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    print("\n=== Calculando HSRI: chamando indicadores de capacidade/demanda/mortalidade ===")

    df_cap = capacidade_assistencial.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_hosp = complexidade_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_pressao = pressao_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_tmh = mortalidade_hospitalar_ajustada.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)

    if df_cap.empty:
        print("⚠️ Nenhum dado disponível para calcular o HSRI.")
        return pd.DataFrame()

    df = df_cap[CHAVES + ['municipio', 'populacao', 'IND_CAPACIDADE_ASSISTENCIAL']].copy()
    df = df.merge(df_hosp[CHAVES + ['N_INTERNACOES_HOSP', 'IND_COMPLEXIDADE_HOSPITALAR']], on=CHAVES, how='left')
    df = df.merge(df_pressao[CHAVES + ['IND_PRESSAO_PERMANENCIA']], on=CHAVES, how='left')
    df = df.merge(df_tmh[CHAVES + ['TMH_HOSPITALAR']], on=CHAVES, how='left')

    colunas = ['IND_CAPACIDADE_ASSISTENCIAL', 'N_INTERNACOES_HOSP', 'IND_COMPLEXIDADE_HOSPITALAR',
               'IND_PRESSAO_PERMANENCIA', 'TMH_HOSPITALAR']
    df[colunas] = df[colunas].fillna(0)

    df['CAPACIDADE_HSRI'] = df['IND_CAPACIDADE_ASSISTENCIAL']
    df['DEMANDA_HSRI'] = combinar_indice_composto(df, ['N_INTERNACOES_HOSP', 'IND_COMPLEXIDADE_HOSPITALAR', 'IND_PRESSAO_PERMANENCIA'])
    df['MORTALIDADE_HSRI'] = combinar_indice_composto(df, ['TMH_HOSPITALAR'])

    # Combinação ADITIVA (não Demanda x Mortalidade) — ver docstring do módulo.
    # Regularização (+1) só no denominador, para não colapsar perto de zero em
    # municípios sem produção hospitalar local, sem alterar o numerador.
    pressao_assistencial = PESO_DEMANDA_HSRI * df['DEMANDA_HSRI'] + PESO_MORTALIDADE_HSRI * df['MORTALIDADE_HSRI']
    razao = df['CAPACIDADE_HSRI'] / (1 + pressao_assistencial)
    df['HSRI'] = _escala_fixa_logistica(razao)

    # Descarta os componentes brutos emprestados (já resumidos em CAPACIDADE_/
    # DEMANDA_/MORTALIDADE_HSRI): outro índice pode reexportar o mesmo
    # indicador de base sem sufixo, e a pipeline de Integração mescla todas
    # as colunas maiúsculas de todos os índices selecionados — mantê-los
    # arriscaria colisão de nomes entre índices diferentes.
    df = df.drop(columns=['IND_CAPACIDADE_ASSISTENCIAL', 'N_INTERNACOES_HOSP', 'IND_COMPLEXIDADE_HOSPITALAR',
                           'IND_PRESSAO_PERMANENCIA', 'TMH_HOSPITALAR'])

    print("✅ HSRI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Healthcare Structural Robustness Index (HSRI).")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "hsri.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
