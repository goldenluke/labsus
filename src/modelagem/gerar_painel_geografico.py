# -*- coding: utf-8 -*-
"""
======================================================================
  PIPELINE PARA GERAÇÃO DO PAINEL DE DADOS GEOGRÁFICOS E CONTEXTUAIS
======================================================================
Este script é responsável por criar um painel de dados consolidado em
nível municipal, integrando informações socioeconômicas e de
infraestrutura de saúde.

O processo envolve:
1. Carregar e consolidar os dados do Índice de Vulnerabilidade Social (IVS)
   do IPEA para os estados selecionados.
2. Carregar os dados do Cadastro Nacional de Estabelecimentos de Saúde (CNES)
   para calcular a quantidade de Unidades Básicas de Saúde (UBS) por município.
3. Juntar as informações, criando um painel de dados contextual que pode ser
   usado para enriquecer outras análises de saúde.
"""

import pandas as pd
from pathlib import Path
import argparse

# Importa a classe CNES para interagir com a base de dados
from pysus.online_data.CNES import CNES

def carregar_dados_contextuais(diretorio_ivs: Path, ufs: list, ano: int):
    """
    Carrega os dados externos de IVS de múltiplos arquivos (um por UF)
    e calcula a quantidade de UBS do CNES para as UFs e ano especificados.
    """
    print(f"\n--- [ETAPA 1] Carregando Dados Contextuais (IVS e CNES) para {ufs}/{ano} ---")

    # --- Carregamento dos dados do IVS ---
    dfs_ivs = []
    print(f"[LOG] Carregando arquivos IVS do diretório: {diretorio_ivs}")
    for uf in ufs:
        # Tenta encontrar o arquivo com sigla maiúscula ou minúscula
        caminho_arquivo_ivs_lower = diretorio_ivs / f"ivs_{uf.lower()}.csv"
        caminho_arquivo_ivs_upper = diretorio_ivs / f"ivs_{uf.upper()}.csv"
        caminho_arquivo_ivs = None

        if caminho_arquivo_ivs_lower.exists():
            caminho_arquivo_ivs = caminho_arquivo_ivs_lower
        elif caminho_arquivo_ivs_upper.exists():
            caminho_arquivo_ivs = caminho_arquivo_ivs_upper

        if caminho_arquivo_ivs:
            try:
                df_uf = pd.read_csv(caminho_arquivo_ivs)
                dfs_ivs.append(df_uf)
                print(f"  -> Arquivo '{caminho_arquivo_ivs.name}' carregado com sucesso.")
            except Exception as e:
                print(f"  -> ⚠️ Aviso: Erro ao ler o arquivo IVS '{caminho_arquivo_ivs}': {e}")
        else:
            print(f"  -> ⚠️ Aviso: Arquivo IVS para {uf} não encontrado.")

    if not dfs_ivs:
        print("❌ Erro: Nenhum arquivo IVS pôde ser carregado para as UFs solicitadas.")
        return None

    df_ivs_completo = pd.concat(dfs_ivs, ignore_index=True)

    # Identifica a coluna correta do município no arquivo IVS
    coluna_municipio_ivs = None
    possiveis_nomes = ['municipio', 'codmun7', 'Codmun', 'codigo_ibge', 'cod_mun', 'codmun']
    for nome in possiveis_nomes:
        if nome in df_ivs_completo.columns:
            coluna_municipio_ivs = nome
            break

    if coluna_municipio_ivs is None:
        print(f"❌ ERRO: Nenhuma coluna de código do município encontrada no CSV do IVS.")
        return None

    df_ivs_completo[coluna_municipio_ivs] = df_ivs_completo[coluna_municipio_ivs].astype(str)
    # Seleciona as colunas de interesse do IVS
    df_ivs_mun = df_ivs_completo.rename(columns={coluna_municipio_ivs: 'CODMUNRES'})
    df_ivs_mun['CODMUNRES'] = df_ivs_mun['CODMUNRES'].str[:6]

    print(f"[LOG] Dados do IVS consolidados.")

    # --- Cálculo da Densidade de UBS a partir do CNES ---
    try:
        print(f"[LOG] Carregando dados do CNES para calcular contagem de UBS...")
        cnes_db = CNES().load()
        files_cnes = cnes_db.get_files(group='ST', uf=ufs, year=ano, month=12)

        if files_cnes:
            downloaded_data = cnes_db.download(files_cnes)
            if isinstance(downloaded_data, list):
                df_cnes_st = pd.concat([f.to_dataframe() for f in downloaded_data], ignore_index=True)
            else:
                df_cnes_st = downloaded_data.to_dataframe()
        else:
            df_cnes_st = pd.DataFrame()

        if not df_cnes_st.empty:
            df_ubs = df_cnes_st[df_cnes_st['TP_UNID'] == '02'] # Filtra por Unidade Básica de Saúde
            contagem_ubs = df_ubs.groupby('CODUFMUN').size().rename('N_UBS').reset_index()
            contagem_ubs.rename(columns={'CODUFMUN': 'CODMUNRES'}, inplace=True)
            contagem_ubs['CODMUNRES'] = contagem_ubs['CODMUNRES'].astype(str)
            print(f"[LOG] Contagem de UBS por município calculada.")
        else:
            contagem_ubs = pd.DataFrame(columns=['CODMUNRES', 'N_UBS'])

    except Exception as e:
        print(f"❌ Erro ao processar CNES para contagem de UBS: {e}")
        return None

    # --- Integração Final ---
    print("\n--- [ETAPA 2] Integrando IVS e dados do CNES ---")
    df_contexto = pd.merge(df_ivs_mun, contagem_ubs, on='CODMUNRES', how='left')
    df_contexto['N_UBS'] = df_contexto['N_UBS'].fillna(0)

    print("✅ Painel de dados geográficos e contextuais criado com sucesso.")
    return df_contexto


def main(args):
    """Ponto de entrada usado tanto pelo CLI (abaixo) quanto pelo runner
    genérico de Modelagem Avançada (api/utils/modelagem_runner.py), que
    monta um objeto `args` equivalente (SimpleNamespace) a partir dos
    parâmetros recebidos do frontend + DEFAULTS_POR_MODULO."""
    df_painel_geo = carregar_dados_contextuais(Path(args.ivs_dir), args.ufs, args.ano)

    if df_painel_geo is None or df_painel_geo.empty:
        print("⚠️ Nenhum painel de dados geográficos foi gerado (ver avisos acima).")
        return

    output_dir = Path(args.dir_saida)
    output_dir.mkdir(parents=True, exist_ok=True)

    ufs_str = '-'.join(args.ufs).lower()
    nome_arquivo = f"painel_geografico_{ufs_str}_{args.ano}.csv"
    caminho_csv = output_dir / nome_arquivo

    df_painel_geo.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')

    print(f"\n📄 Painel de dados geográficos salvo com sucesso em: '{caminho_csv}'")
    print("\n--- Amostra do Painel Gerado ---")
    print(df_painel_geo.head())

    print("\n" + "="*80)
    print("🎉 PIPELINE DE GERAÇÃO DE DADOS CONTEXTUAIS CONCLUÍDO! 🎉")
    print("="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera um painel de dados geográficos consolidando IVS e informações do CNES.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--ivs-dir", type=str, default="referencia/ipea", help="Caminho para o DIRETÓRIO contendo os arquivos CSV do IVS por estado.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência para os dados do CNES.")
    parser.add_argument("--dir_saida", type=str, default="dados/processados/contextuais", help="Diretório de saída para o painel de dados gerado.")

    args = parser.parse_args()
    main(args)
