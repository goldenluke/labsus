# -*- coding: utf-8 -*-
"""
======================================================================
  SCRIPT DE DIAGNÓSTICO PARA DADOS DO SINAN-TUBERCULOSE
======================================================================
Este script carrega dados de Tuberculose de dois períodos distintos
(antes e depois de uma mudança de sistema) e compara a estrutura e o
conteúdo das colunas-chave para identificar inconsistências.
"""

import pandas as pd
from pathlib import Path
import argparse

from pysus.online_data.SINAN import SINAN

def carregar_dados_para_inspecao(ano: int, ufs: list):
    """Carrega dados de um ano específico para inspeção."""
    print(f"\n--- Carregando dados do SINAN-TB para {ufs}/{ano} ---")
    try:
        sinan_db = SINAN().load()
        files = sinan_db.get_files(dis_code='TUBE', year=ano)
        if not files:
            print(f"⚠️ Nenhum arquivo encontrado para {ano}.")
            return pd.DataFrame()

        downloaded = sinan_db.download(files)
        if isinstance(downloaded, list):
            df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True)
        else:
            df = downloaded.to_dataframe()
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar dados para o ano {ano}: {e}")
        return pd.DataFrame()

def inspecionar_variaveis(df: pd.DataFrame, ano: int):
    """Imprime um resumo das colunas-chave para um DataFrame."""
    print("\n" + "="*50)
    print(f"🔎 INSPECIONANDO DADOS DO ANO DE {ano}")
    print("="*50)

    if df.empty:
        print("DataFrame está vazio. Nenhuma análise possível.")
        return

    colunas_chave = ['TRATAMENTO', 'SITUA_ENCE', 'DT_ENCERRA']

    for col in colunas_chave:
        print(f"\n--- Análise da Coluna: '{col}' ---")
        if col in df.columns:
            print(f"Tipo de Dado (dtype): {df[col].dtype}")
            print("Valores Únicos e Contagens:")
            print(df[col].value_counts(dropna=False).sort_index())
            print(f"Total de Nulos (NaN): {df[col].isnull().sum()}")
        else:
            print("Coluna não encontrada no DataFrame.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inspeci_ona e compara a estrutura de dados do SINAN-TB entre dois períodos."
    )
    parser.add_argument("--ufs", nargs="+", required=True, help="Lista de UFs a processar.")
    parser.add_argument("--ano_antes", type=int, required=True, help="Um ano ANTES da mudança do sistema (ex: 2013).")
    parser.add_argument("--ano_depois", type=int, required=True, help="Um ano DEPOIS da mudança do sistema (ex: 2014).")
    args = parser.parse_args()

    # Carrega os dados para os dois períodos
    df_antes = carregar_dados_para_inspecao(args.ano_antes, args.ufs)
    df_depois = carregar_dados_para_inspecao(args.ano_depois, args.ufs)

    # Executa a inspeção para cada período
    inspecionar_variaveis(df_antes, args.ano_antes)
    inspecionar_variaveis(df_depois, args.ano_depois)

    print("\n" + "="*50)
    print("🕵️  INSPEÇÃO CONCLUÍDA 🕵️")
    print("Compare os resultados acima para identificar diferenças nos tipos de dados ou nos códigos utilizados.")
    print("="*50)
