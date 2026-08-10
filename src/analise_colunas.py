# -*- coding: utf-8 -*-
"""
======================================================================
  SCRIPT DE ANÁLISE EXPLORATÓRIA DAS BASES DE DADOS DO DATASUS
======================================================================
Este script se conecta aos principais sistemas de informação em saúde
do Brasil via PySUS, baixa um arquivo de exemplo de cada um, e lista
todas as colunas disponíveis.

É uma ferramenta essencial para entender os dados antes de construir
pipelines de processamento.

Como usar:
- Execute o script em um ambiente com PySUS e suas dependências instaladas.
- O script irá imprimir a lista de colunas para cada base de dados.
"""

import pandas as pd
# Importa as classes diretamente do pacote principal 'pysus'
from pysus import CNES, SINAN, SINASC, SIM, SIA, SIH
from typing import Optional

# --- Configurações Gerais ---
# Usamos um estado e ano fixos para obter exemplos consistentes.
# Tocantins (TO) e 2022 são boas escolhas.
UF_EXEMPLO = 'TO'
ANO_EXEMPLO = 2022

def analisar_base(database_class, nome_base: str, **kwargs) -> Optional[pd.DataFrame]:
    """
    Função genérica para baixar e analisar uma base de dados do PySUS.

    Args:
        database_class: A classe da base de dados do PySUS (ex: SINAN, SIM).
        nome_base (str): Nome amigável da base para os logs.
        **kwargs: Argumentos para a função get_files() (ex: group, dis_code).

    Returns:
        Um DataFrame do pandas com os dados ou None em caso de erro.
    """
    print("-" * 70)
    print(f"🔎 Analisando: {nome_base}")
    print("-" * 70)

    try:
        # 1. Carrega a definição da base de dados
        db = database_class().load()
        print(f"[LOG] Definições de '{nome_base}' carregadas.")

        # 2. Busca por um arquivo de exemplo
        print(f"[LOG] Buscando arquivos para o ano {ANO_EXEMPLO}...")
        files = db.get_files(year=ANO_EXEMPLO, **kwargs)

        if not files:
            print(f"⚠️ Nenhum arquivo encontrado para '{nome_base}' com os parâmetros fornecidos. Pulando.")
            return None

        # Pega apenas o primeiro arquivo como amostra
        arquivo_amostra = files[0]
        print(f"[LOG] Arquivo de amostra encontrado: {arquivo_amostra.name}")

        # 3. Baixa e converte para DataFrame
        print("[LOG] Baixando e convertendo para DataFrame...")
        df = arquivo_amostra.download().to_dataframe()
        print("[LOG] Download e conversão concluídos com sucesso.")

        return df

    except Exception as e:
        print(f"❌ Erro ao processar a base '{nome_base}': {e}")
        return None

def main():
    """
    Função principal que orquestra a análise de todas as bases de dados.
    """
    # 1. CNES - Cadastro Nacional de Estabelecimentos de Saúde
    df_cnes = analisar_base(CNES, "CNES - Estabelecimentos", group='ST', uf=UF_EXEMPLO)
    if df_cnes is not None:
        print("\n✅ Colunas do CNES (Estabelecimentos):")
        print(df_cnes.columns.tolist())
        print(f"\nTotal de colunas: {len(df_cnes.columns)}\n")

    # 2. SINAN - Sistema de Informação de Agravos de Notificação
    df_sinan = analisar_base(SINAN, "SINAN - Acidente por Animais Peçonhentos", dis_code='ANIM')
    if df_sinan is not None:
        print("\n✅ Colunas do SINAN (Acidente por Animais Peçonhentos):")
        print(df_sinan.columns.tolist())
        print(f"\nTotal de colunas: {len(df_sinan.columns)}\n")

    # 3. SINASC - Sistema de Informações sobre Nascidos Vivos
    df_sinasc = analisar_base(SINASC, "SINASC - Nascidos Vivos", group='DN', uf=UF_EXEMPLO)
    if df_sinasc is not None:
        print("\n✅ Colunas do SINASC (Nascidos Vivos):")
        print(df_sinasc.columns.tolist())
        print(f"\nTotal de colunas: {len(df_sinasc.columns)}\n")

    # 4. SIM - Sistema de Informação sobre Mortalidade
    df_sim = analisar_base(SIM, "SIM - Mortalidade", group='CID10', uf=UF_EXEMPLO)
    if df_sim is not None:
        print("\n✅ Colunas do SIM (Mortalidade):")
        print(df_sim.columns.tolist())
        print(f"\nTotal de colunas: {len(df_sim.columns)}\n")

    # 5. SIA - Sistema de Informações Ambulatoriais
    df_sia = analisar_base(SIA, "SIA - Produção Ambulatorial", group='PA', uf=UF_EXEMPLO, month=1)
    if df_sia is not None:
        print("\n✅ Colunas do SIA (Produção Ambulatorial):")
        print(df_sia.columns.tolist())
        print(f"\nTotal de colunas: {len(df_sia.columns)}\n")

    # 6. SIH - Sistema de Informações Hospitalares
    df_sih = analisar_base(SIH, "SIH - Internações Hospitalares", group='RD', uf=UF_EXEMPLO, month=1)
    if df_sih is not None:
        print("\n✅ Colunas do SIH (Internações):")
        print(df_sih.columns.tolist())
        print(f"\nTotal de colunas: {len(df_sih.columns)}\n")

if __name__ == "__main__":
    main()
