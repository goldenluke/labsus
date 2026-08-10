# -*- coding: utf-8 -*-
"""
======================================================================
  HEALTHCARE SYSTEM STRESS INDEX (HSSI)
======================================================================
Objetivo: mensurar a sobrecarga da rede hospitalar de um município.

Indicadores usados (src/features/):
  - pressao_hospitalar.IND_PRESSAO_LEITOS       (internações/leito)
  - pressao_hospitalar.IND_PRESSAO_PERMANENCIA  (dias de permanência/leito)
  - mortalidade_hospitalar_ajustada.TMH_HOSPITALAR  (proxy p/ mortalidade/leito)
  - complexidade_hospitalar.IND_COMPLEXIDADE_HOSPITALAR (proxy p/
    procedimentos de alta complexidade/leito)

Método: HSSI = combinar_indice_composto() dos quatro componentes acima
— 1ª componente principal, reescalada 0-100. Município com HSSI alto
está sob mais pressão simultânea (ocupação, permanência, gravidade e
complexidade) sobre a capacidade instalada local.
"""
import pandas as pd

from ..features import pressao_hospitalar, mortalidade_hospitalar_ajustada, complexidade_hospitalar
from ..utils.indices_compostos import combinar_indice_composto

CHAVES = ['cod_mun_ibge_6', 'ANO', 'UF']


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    print("\n=== Calculando HSSI: chamando indicadores de pressão/mortalidade/complexidade hospitalar ===")

    df_pressao = pressao_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_tmh = mortalidade_hospitalar_ajustada.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_hosp = complexidade_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)

    if df_pressao.empty:
        print("⚠️ Nenhum dado disponível para calcular o HSSI.")
        return pd.DataFrame()

    df = df_pressao[CHAVES + ['municipio', 'populacao', 'IND_PRESSAO_LEITOS', 'IND_PRESSAO_PERMANENCIA']].copy()
    df = df.merge(df_tmh[CHAVES + ['TMH_HOSPITALAR']], on=CHAVES, how='left')
    df = df.merge(df_hosp[CHAVES + ['IND_COMPLEXIDADE_HOSPITALAR']], on=CHAVES, how='left')

    colunas = ['IND_PRESSAO_LEITOS', 'IND_PRESSAO_PERMANENCIA', 'TMH_HOSPITALAR', 'IND_COMPLEXIDADE_HOSPITALAR']
    df[colunas] = df[colunas].fillna(0)

    df['HSSI'] = combinar_indice_composto(df, colunas)

    # Todos os quatro componentes acima já são nomes de indicadores de 1ª
    # camada (pressao_hospitalar.py, mortalidade_hospitalar_ajustada.py,
    # complexidade_hospitalar.py) — se o usuário selecionar as duas camadas
    # na mesma integração, colidiriam com as colunas deste índice. Renomeia
    # com o sufixo _HSSI.
    df = df.rename(columns={col: f'{col}_HSSI' for col in colunas})

    print("✅ HSSI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Healthcare System Stress Index (HSSI).")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "hssi.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
