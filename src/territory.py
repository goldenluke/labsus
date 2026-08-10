# -*- coding: utf-8 -*-
import pandas as pd
import os

def gerar_populacao_historica_brasil():
    """
    Baixa e processa a série histórica de estimativas populacionais por município
    do IPEADATA, transformando-a em um painel de dados (formato longo).
    """
    print("Iniciando o processo para gerar a série histórica de população...")

    # URL para a série histórica de população municipal do IPEADATA (1991-2020)
    # Nota: Esta é uma fonte consolidada e confiável.
    url_ipea = "http://www.ipeadata.gov.br/Default.aspx?DataSetId=6&SerieId=36495&module=M"

    # Como o IPEA não oferece um link CSV direto, usaremos um mirror confiável do arquivo
    url_mirror = "https://raw.githubusercontent.com/datascience-br/populacao-brasileira/master/data/populacao_brasileira_1991_2020.csv"

    try:
        print(f"Baixando dados de: {url_mirror}")
        # Lê o arquivo, que usa vírgula como separador
        df_wide = pd.read_csv(url_mirror, sep=',')
        print("Download concluído. Transformando os dados de formato largo para longo...")

        # --- Transformação com pd.melt() ---

        # Colunas que serão mantidas fixas (identificadores)
        id_vars = ['Codmun', 'Município', 'Estado']

        # Colunas que serão transformadas em linhas (os anos)
        value_vars = [col for col in df_wide.columns if col.startswith('POP')]

        df_long = pd.melt(
            df_wide,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name='ANO',
            value_name='populacao'
        )

        # --- Limpeza e Formatação ---

        # 1. Limpa a coluna 'ANO', removendo o prefixo 'POP' e convertendo para número
        df_long['ANO'] = df_long['ANO'].str.replace('POP', '').astype(int)

        # 2. Renomeia as colunas para o padrão desejado
        df_long.rename(columns={
            'Codmun': 'cod_mun_ibge_7',
            'Município': 'municipio',
            'Estado': 'estado'
        }, inplace=True)

        # 3. Garante que os códigos sejam tratados como texto
        df_long['cod_mun_ibge_7'] = df_long['cod_mun_ibge_7'].astype(str)

        # 4. Cria a coluna com o código IBGE de 6 dígitos
        df_long['cod_mun_ibge_6'] = df_long['cod_mun_ibge_7'].str[:6]

        # 5. Remove linhas com população nula ou zero (geralmente municípios que ainda não existiam)
        df_long.dropna(subset=['populacao'], inplace=True)
        df_long = df_long[df_long['populacao'] > 0]
        df_long['populacao'] = df_long['populacao'].astype(int)

        # 6. Reordena as colunas para o formato final
        colunas_finais = ['cod_mun_ibge_7', 'municipio', 'estado', 'ANO', 'populacao', 'cod_mun_ibge_6']
        df_final = df_long[colunas_finais]

        print(f"Processamento concluído. Total de {df_final.shape[0]} registros (município-ano) gerados.")

        # --- Salvando o arquivo ---
        output_filename = "populacao_brasil_historico_1991-2020.csv"
        df_final.to_csv(output_filename, sep=';', encoding='utf-8-sig', index=False)

        print(f"\n✅ Arquivo '{output_filename}' salvo com sucesso!")
        print("\n--- Amostra dos dados gerados ---")
        print(df_final.head())
        print("...")
        print(df_final.tail())

    except Exception as e:
        print(f"\n❌ Ocorreu um erro durante o processo: {e}")
        print("Por favor, verifique sua conexão com a internet e tente novamente.")

# Executa a função principal
if __name__ == "__main__":
    gerar_populacao_historica_brasil()
