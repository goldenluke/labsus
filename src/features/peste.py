# -*- coding: utf-8 -*-
# Arquivo: src/features/peste.py
# Indicador: Peste (SINAN/PEST)

import argparse
from pathlib import Path
from ..utils.dataloaders import processar_agravo_sinan_generico

DIS_CODE = "PEST"
NOME_INDICADOR = "TAXA_INCIDENCIA_PESTE"


def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """Calcula a taxa de incidência de peste (por 100.000 hab.) a partir do SINAN/PEST."""
    return processar_agravo_sinan_generico(
        ufs, anos, arquivo_populacao,
        dis_code=DIS_CODE,
        nome_indicador=NOME_INDICADOR,
        coluna_filtro='CLASSI_FIN',
        codigos_confirmados=['1'],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a Peste (SINAN/PEST).")
    parser.add_argument("--ufs", nargs="+", required=True, help="Lista de UFs (ex: TO SP).")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Lista de anos (ex: 2023 2024).")
    parser.add_argument("--populacao", required=True, help="Caminho para o CSV de população estimada.")
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.populacao)
    if df_resultado is not None and not df_resultado.empty:
        print(df_resultado.head(20))
        print(f"\nTotal de linhas: {len(df_resultado)}")
    else:
        print("Nenhum dado retornado.")
