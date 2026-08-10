# -*- coding: utf-8 -*-
"""
Módulo para realizar a previsão de internações por grupo de doenças (CID-10),
utilizando dados do Sistema de Informações Hospitalares (SIH/SUS) e o Prophet.
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# --- IMPORTAÇÃO DO PYSUS ---
from pysus.online_data.SIH import SIH

def carregar_dados_sih(ufs: list, anos: list, cid_codes: list):
    """
    Carrega e processa dados do SIH para um período e UFs específicos,
    filtrando por um prefixo de capítulo da CID-10 ou uma lista de códigos.

    :param ufs: Lista de siglas de UFs a serem processadas (ex: ['TO', 'SP']).
    :param anos: Lista de anos a serem processados (ex: [2022, 2023]).
    :param cid_codes: Lista de códigos CID-10 para filtrar (ex: ['J'] ou ['J18', 'J15']).
    :return: DataFrame agregado semanalmente, pronto para o Prophet.
    """
    cid_str_log = ", ".join(cid_codes)
    print(f"\n[LOG] Iniciando carregamento de dados do SIH para os códigos CID '{cid_str_log}'...")

    try:
        sih_db = SIH()
        sih_db.load()

        dfs_sih = []
        for ano in anos:
            for uf in ufs:
                files = sih_db.get_files(group='RD', uf=uf, year=ano)
                if files:
                    print(f"[DEBUG] Baixando {len(files)} arquivo(s) SIH/RD para {uf}/{ano}...")
                    parquet_set = sih_db.download(files)
                    if isinstance(parquet_set, list):
                        dfs_sih.extend([p.to_dataframe() for p in parquet_set])
                    elif hasattr(parquet_set, "to_dataframe"):
                        dfs_sih.append(parquet_set.to_dataframe())

        if not dfs_sih:
            print("[AVISO] Nenhum arquivo do SIH foi encontrado para o período/UF especificado.")
            return pd.DataFrame()

        df_sih_full = pd.concat(dfs_sih, ignore_index=True)
        print(f"[DEBUG] SIH: Total de {len(df_sih_full)} registros baixados para {', '.join(ufs)} nos anos {anos}.")

        # --- CORREÇÃO APLICADA AQUI: Lógica de filtro flexível ---
        # Separa códigos de prefixo (1 letra) de códigos completos (3+ letras)
        prefixes = [code for code in cid_codes if len(code) == 1]
        full_codes = [code for code in cid_codes if len(code) >= 3]

        # Cria máscaras booleanas para cada tipo de filtro
        mask_prefix = pd.Series(False, index=df_sih_full.index)
        if prefixes:
            mask_prefix = df_sih_full['DIAG_PRINC'].str.startswith(tuple(prefixes), na=False)

        mask_full = pd.Series(False, index=df_sih_full.index)
        if full_codes:
            mask_full = df_sih_full['DIAG_PRINC'].isin(full_codes)

        # Combina as máscaras com um OU lógico
        df_filtrado_causa = df_sih_full[mask_prefix | mask_full].copy()
        print(f"[DEBUG] Filtrados {len(df_filtrado_causa)} registros para os códigos CID fornecidos.")

        # --- Passo 2: Filtrar por Local (UF de Residência) ---
        df_filtrado_causa['UF_RES_COD'] = df_filtrado_causa['MUNIC_RES'].str[:2]

        mapa_uf = {
            '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
            '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
            '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
            '41': 'PR', '42': 'SC', '43': 'RS',
            '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
        }
        df_filtrado_causa['UF_RES'] = df_filtrado_causa['UF_RES_COD'].map(mapa_uf)

        df_filtrado_uf = df_filtrado_causa[df_filtrado_causa['UF_RES'].isin(ufs)].copy()
        print(f"[DEBUG] Mantidos {len(df_filtrado_uf)} registros para residentes de {', '.join(ufs)}.")

        # --- Passo 3: Agregar os Dados (Contagem Semanal) ---
        df_filtrado_uf['DT_INTER'] = pd.to_datetime(df_filtrado_uf['DT_INTER'], errors='coerce')
        df_filtrado_uf.dropna(subset=['DT_INTER'], inplace=True)

        serie_temporal = df_filtrado_uf.groupby(pd.Grouper(key='DT_INTER', freq='W-Mon'))['N_AIH'].nunique().rename('y').reset_index()
        serie_temporal.rename(columns={'DT_INTER': 'ds'}, inplace=True)

        print("[LOG] Dados agregados semanalmente com sucesso.")
        print("[DEBUG] Amostra da série temporal final:")
        print(serie_temporal.head())

        return serie_temporal

    except Exception as e:
        print(f"❌ ERRO CRÍTICO durante o carregamento de dados: {e}")
        return pd.DataFrame()


def executar_previsao(ufs: list, anos_historico: list, cid_codes: list, meses_previsao: int, dir_saida_previsao: Path):
    """
    Orquestra todo o processo de previsão de internações por grupo de doenças.
    """
    cid_str_log = ", ".join(cid_codes)
    print(f"\n--- Iniciando Previsão para CID(s) '{cid_str_log}' em {', '.join(ufs)} ---")

    df_historico = carregar_dados_sih(ufs=ufs, anos=anos_historico, cid_codes=cid_codes)

    if df_historico.empty or df_historico['y'].sum() == 0:
        print(f"❌ ERRO: Não foram encontrados dados de internação para CID(s) '{cid_str_log}' nos filtros aplicados. Previsão abortada.")
        return

    df_historico['floor'] = 0
    df_historico['cap'] = df_historico['y'].max() * 1.5

    # --- Treinamento do Modelo Prophet ---
    print("\n[LOG] Treinando o modelo Prophet com crescimento logístico...")

    modelo = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode='multiplicative',
        growth='logistic'
    )

    modelo.fit(df_historico)
    print("[LOG] Modelo treinado com sucesso.")

    # --- Geração da Previsão ---
    periodos_futuros = int(np.ceil((meses_previsao * 30.5) / 7)) # Converte meses em semanas
    print(f"\n[LOG] Gerando datas futuras para {periodos_futuros} semanas de previsão...")
    futuro = modelo.make_future_dataframe(periods=periodos_futuros, freq='W-Mon')

    futuro['floor'] = 0
    futuro['cap'] = df_historico['cap'].iloc[0]

    print("\n[LOG] Realizando a previsão...")
    previsao = modelo.predict(futuro)
    print("[LOG] Previsão concluída.")

    # --- Salvando Resultados ---
    dir_saida_previsao.mkdir(parents=True, exist_ok=True)
    ufs_str = '_'.join(ufs).lower()
    cid_str = '_'.join(cid_codes).lower()

    # Salvar CSV
    nome_arquivo_csv = f"previsao_cid_{cid_str}_{ufs_str}.csv"
    caminho_csv = dir_saida_previsao / nome_arquivo_csv
    previsao[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_csv(
        caminho_csv, sep=';', encoding='utf-8-sig', index=False
    )
    print(f"✅ Previsão em CSV salva em: {caminho_csv}")

    # Salvar Gráficos
    fig1 = modelo.plot(previsao, xlabel='Data', ylabel='Internações Semanais')
    ax1 = fig1.gca()
    ax1.set_title(f"Previsão de Internações (CID: {cid_str_log}) - UFs: {', '.join(ufs)}", size=16)
    caminho_grafico1 = dir_saida_previsao / f"grafico_previsao_cid_{cid_str}_{ufs_str}.png"
    fig1.savefig(caminho_grafico1, dpi=300)
    plt.close(fig1)
    print(f"📈 Gráfico de previsão salvo em: {caminho_grafico1}")

    fig2 = modelo.plot_components(previsao)
    caminho_grafico2 = dir_saida_previsao / f"grafico_componentes_cid_{cid_str}_{ufs_str}.png"
    fig2.savefig(caminho_grafico2, dpi=300)
    plt.close(fig2)
    print(f"📊 Gráfico de componentes salvo em: {caminho_grafico2}")


if __name__ == '__main__':
    help_text_cid = """
    Um ou mais códigos CID-10 para filtrar as internações.
    - Para um capítulo inteiro, use a letra (ex: J).
    - Para doenças específicas, use os códigos completos (ex: J18 J15).
    Exemplos de Capítulos:
    A, B: Doenças infecciosas e parasitárias
    C: Neoplasias (tumores)
    I: Doenças do aparelho circulatório
    J: Doenças do aparelho respiratório
    K: Doenças do aparelho digestivo
    S, T: Lesões e envenenamentos
    """

    parser = argparse.ArgumentParser(
        description="Executa a previsão de internações por grupo de doenças (CID-10) usando dados do SIH/SUS.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--cid", nargs="+", default=["I"], help=help_text_cid)
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de siglas de UFs a processar. Ex: TO SP RJ")
    parser.add_argument("--anos", nargs="+", type=int, default=[2023, 2024, 2025], help="Anos de dados históricos a usar.")
    parser.add_argument("--meses_futuros", type=int, default=6, help="Número de meses a prever no futuro.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsoes_por_cid", help="Diretório para salvar os resultados.")

    args = parser.parse_args()

    # Garante que os códigos CID sejam maiúsculos
    cid_codes_upper = [code.upper() for code in args.cid]

    executar_previsao(
        ufs=args.ufs,
        anos_historico=args.anos,
        cid_codes=cid_codes_upper,
        meses_previsao=args.meses_futuros,
        dir_saida_previsao=Path(args.dir_saida)
    )
