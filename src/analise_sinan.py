# -*- coding: utf-8 -*-
"""
======================================================================
  SCRIPT DE ANÁLISE EXPLORATÓRIA DAS BASES DE DADOS DO DATASUS
======================================================================
Este script se conecta aos principais sistemas de informação em saúde
do Brasil via PySUS, baixa um arquivo de exemplo de cada um, e lista
todas as colunas disponíveis.

Como usar:
- Execute o script. A saída será exibida na tela e também salva no
  arquivo 'analise_completa_datasus.txt'.
"""

import pandas as pd
from pysus import CNES, SINAN, SINASC, SIM, SIA, SIH
from typing import Optional
import sys

# --- Configurações Gerais ---
# Usando 2023 como um ano recente e com dados mais consolidados.
UF_EXEMPLO = 'TO'
ANO_EXEMPLO = 2023

def log(message, file_handle):
    """Função de log que imprime na tela e no arquivo."""
    print(message)
    if file_handle and not file_handle.closed:
        file_handle.write(message + '\n')

def analisar_base(database_class, nome_base: str, logger_func, file_handle, **kwargs) -> Optional[pd.DataFrame]:
    """Função genérica para baixar e analisar uma base de dados do PySUS."""
    logger_func("-" * 70, file_handle)
    logger_func(f"🔎 Analisando: {nome_base}", file_handle)
    logger_func("-" * 70, file_handle)
    try:
        db = database_class().load()
        logger_func(f"[LOG] Definições de '{nome_base}' carregadas.", file_handle)
        logger_func(f"[LOG] Buscando arquivos para o ano {ANO_EXEMPLO}...", file_handle)
        files = db.get_files(year=ANO_EXEMPLO, **kwargs)
        if not files:
            logger_func(f"⚠️ Nenhum arquivo encontrado para '{nome_base}'. Pulando.", file_handle)
            return None
        arquivo_amostra = files[0]
        logger_func(f"[LOG] Arquivo de amostra encontrado: {arquivo_amostra.name}", file_handle)
        logger_func("[LOG] Baixando e convertendo para DataFrame...", file_handle)
        df = arquivo_amostra.download().to_dataframe()
        logger_func("[LOG] Download e conversão concluídos.", file_handle)
        return df
    except Exception as e:
        logger_func(f"❌ Erro ao processar a base '{nome_base}': {e}", file_handle)
        return None

def main(logger_func, file_handle):
    """Função principal que orquestra a análise de todas as bases de dados."""
    # 1. CNES
    df_cnes = analisar_base(CNES, "CNES - Estabelecimentos", logger_func, file_handle, group='ST', uf=UF_EXEMPLO)
    if df_cnes is not None:
        logger_func("\n✅ Colunas do CNES (Estabelecimentos):", file_handle)
        logger_func(str(df_cnes.columns.tolist()), file_handle)
        logger_func(f"\nTotal de colunas: {len(df_cnes.columns)}\n", file_handle)

    # 2. SINAN
    logger_func("\n" + "="*70, file_handle)
    logger_func("INICIANDO ANÁLISE DE TODOS OS AGRAVOS DO SINAN", file_handle)
    logger_func("="*70 + "\n", file_handle)
    try:
        db_sinan_ref = SINAN().load()
        todos_dis_codes = sorted(db_sinan_ref.diseases.keys())
        logger_func(f"Encontrados {len(todos_dis_codes)} agravos no SINAN.", file_handle)

        # Lista de agravos a serem ignorados
        agravos_a_pular = ['DENG', 'VIOL']

        for code in todos_dis_codes:
            # ==========================================================
            # MODIFICAÇÃO PARA EXCLUIR DENGUE E VIOLÊNCIA
            # ==========================================================
            if code in agravos_a_pular:
                nome_doenca = db_sinan_ref.diseases.get(code, "Desconhecido")
                logger_func(f"\n---\n[AVISO] Pulando o agravo '{code}' ({nome_doenca}) conforme solicitado.\n---", file_handle)
                continue # Pula para a próxima iteração do loop
            # ==========================================================

            nome_doenca = db_sinan_ref.diseases.get(code, "Desconhecido")
            nome_base_analise = f"SINAN - {nome_doenca} ({code})"
            df_sinan = analisar_base(SINAN, nome_base_analise, logger_func, file_handle, dis_code=code)
            if df_sinan is not None:
                logger_func(f"\n✅ Colunas para {nome_base_analise}:", file_handle)
                logger_func(str(df_sinan.columns.tolist()), file_handle)
                logger_func(f"\nTotal de colunas: {len(df_sinan.columns)}\n", file_handle)
    except Exception as e:
        logger_func(f"❌ Erro geral ao processar o SINAN: {e}", file_handle)

    # 3. SINASC
    df_sinasc = analisar_base(SINASC, "SINASC - Nascidos Vivos", logger_func, file_handle, group='DN', uf=UF_EXEMPLO)
    if df_sinasc is not None:
        logger_func("\n✅ Colunas do SINASC (Nascidos Vivos):", file_handle)
        logger_func(str(df_sinasc.columns.tolist()), file_handle)
        logger_func(f"\nTotal de colunas: {len(df_sinasc.columns)}\n", file_handle)

    # 4. SIM
    df_sim = analisar_base(SIM, "SIM - Mortalidade", logger_func, file_handle, group='DO', uf=UF_EXEMPLO)
    if df_sim is not None:
        logger_func("\n✅ Colunas do SIM (Mortalidade):", file_handle)
        logger_func(str(df_sim.columns.tolist()), file_handle)
        logger_func(f"\nTotal de colunas: {len(df_sim.columns)}\n", file_handle)

    # 5. SIA
    df_sia = analisar_base(SIA, "SIA - Produção Ambulatorial", logger_func, file_handle, group='PA', uf=UF_EXEMPLO, month=1)
    if df_sia is not None:
        logger_func("\n✅ Colunas do SIA (Produção Ambulatorial):", file_handle)
        logger_func(str(df_sia.columns.tolist()), file_handle)
        logger_func(f"\nTotal de colunas: {len(df_sia.columns)}\n", file_handle)

    # 6. SIH
    df_sih = analisar_base(SIH, "SIH - Internações Hospitalares", logger_func, file_handle, group='RD', uf=UF_EXEMPLO, month=1)
    if df_sih is not None:
        logger_func("\n✅ Colunas do SIH (Internações):", file_handle)
        logger_func(str(df_sih.columns.tolist()), file_handle)
        logger_func(f"\nTotal de colunas: {len(df_sih.columns)}\n", file_handle)

if __name__ == "__main__":
    try:
        with open('analise_completa_datasus.txt', 'w', encoding='utf-8') as f:
            log("Iniciando a análise... A saída será exibida na tela e salva em 'analise_completa_datasus.txt'", f)
            main(log, f)
        print("\nAnálise concluída. Verifique o arquivo 'analise_completa_datasus.txt'.")
    except Exception as e:
        print(f"\nOcorreu um erro crítico: {e}")
