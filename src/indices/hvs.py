# -*- coding: utf-8 -*-
"""
======================================================================
  HEALTHCARE VULNERABILITY SCORE (HVS)
======================================================================
Objetivo: mensurar a vulnerabilidade estrutural de um município frente
ao seu próprio sistema de saúde.

Ideia: maior cobertura de recursos → menor vulnerabilidade; maior
mortalidade evitável → maior vulnerabilidade.

Indicadores usados (src/features/):
  - capacidade_assistencial.IND_CAPACIDADE_ASSISTENCIAL  → cobertura de
    recursos (leitos/médicos/enfermeiros/eSF) — quanto MAIOR, menor a
    vulnerabilidade, então entra invertido na fórmula.
  - doencas_cronicas.DOENCAS_CRONICAS → internações por condições
    sensíveis à atenção primária (ICSAP), proxy direto de falha de
    atenção básica.
  - mortalidade_infantil.TMI → proxy de mortalidade evitável (um dos
    indicadores de mortalidade evitável mais estabelecidos na
    literatura de saúde pública).

Método: HVS = combinar_indice_composto([100 - capacidade_normalizada,
ICSAP, TMI]) — 1ª componente principal, reescalada 0-100. Município com
HVS alto tem pouca capacidade instalada E alta pressão evitável sobre o
sistema — o perfil de maior vulnerabilidade estrutural.
"""
import pandas as pd

from ..features import capacidade_assistencial, doencas_cronicas, mortalidade_infantil
from ..utils.indices_compostos import combinar_indice_composto

CHAVES = ['cod_mun_ibge_6', 'ANO', 'UF']


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    print("\n=== Calculando HVS: chamando indicadores de capacidade/ICSAP/mortalidade evitável ===")

    df_cap = capacidade_assistencial.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_icsap = doencas_cronicas.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao, meses=meses)
    df_tmi = mortalidade_infantil.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)

    if df_cap.empty:
        print("⚠️ Nenhum dado disponível para calcular o HVS.")
        return pd.DataFrame()

    df = df_cap[CHAVES + ['municipio', 'populacao', 'IND_CAPACIDADE_ASSISTENCIAL']].copy()

    if not df_icsap.empty and 'DOENCAS_CRONICAS' in df_icsap.columns:
        df = df.merge(df_icsap[CHAVES + ['DOENCAS_CRONICAS']], on=CHAVES, how='left')
    else:
        df['DOENCAS_CRONICAS'] = 0

    if not df_tmi.empty and 'TMI' in df_tmi.columns:
        df = df.merge(df_tmi[CHAVES + ['TMI']], on=CHAVES, how='left')
    else:
        df['TMI'] = 0

    df[['DOENCAS_CRONICAS', 'TMI']] = df[['DOENCAS_CRONICAS', 'TMI']].fillna(0)

    df['INVERSO_CAPACIDADE_HVS'] = 100 - df['IND_CAPACIDADE_ASSISTENCIAL']
    df['HVS'] = combinar_indice_composto(df, ['INVERSO_CAPACIDADE_HVS', 'DOENCAS_CRONICAS', 'TMI'])

    # DOENCAS_CRONICAS e TMI já são nomes de indicadores de 1ª camada
    # (doencas_cronicas.py, mortalidade_infantil.py) — se o usuário selecionar
    # ambas as camadas na mesma integração, colidiriam com as colunas deste
    # índice. Renomeia com o sufixo _HVS e descarta o componente bruto de
    # capacidade (já resumido em INVERSO_CAPACIDADE_HVS).
    df = df.rename(columns={'DOENCAS_CRONICAS': 'DOENCAS_CRONICAS_HVS', 'TMI': 'TMI_HVS'})
    df = df.drop(columns=['IND_CAPACIDADE_ASSISTENCIAL'])

    print("✅ HVS processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Healthcare Vulnerability Score (HVS).")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "hvs.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
