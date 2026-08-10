# --- ARQUIVO CORRIGIDO E FOCADO: previsao.py ---
# -*- coding: utf-8 -*-
"""
Módulo para realizar a previsão de demanda de medicamentos utilizando o Prophet,
com capacidade de carregar dados reais do DataSUS via PySUS para uma lista de medicamentos.
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# --- IMPORTAÇÕES DO PYSUS ---
from pysus.online_data.SIA import SIA
from pysus.online_data.SIH import SIH
from pysus.online_data.CNES import CNES

# --- DICIONÁRIO DE CONFIGURAÇÃO DOS MEDICAMENTOS/PROCEDIMENTOS ---
# Adicione ou modifique os medicamentos aqui.
# IMPORTANTE: A disponibilidade dos códigos pode variar por estado e ano.
# Verifique os códigos corretos em portais como o SIGTAP e a documentação do CNES.
MEDICAMENTOS_CONFIG = {
    "CONSULTA_MEDICA": {
        "proc_sia": "0301010072", # CONSULTA MEDICA ESPECIALIZADA
        "cid_sih": "I10",        # Hipertensão essencial (primária)
        "leito_cnes": "2"       # Leito Clínico
    },
    "CATETERISMO_CARDIACO": {
        "proc_sia": "0303010012",
        "cid_sih": "I50",        # Insuficiência cardíaca
        "leito_cnes": "2"       # Leito Clínico
    },
    "TRASTUZUMABE": {
        "proc_sia": "0604360017",
        "cid_sih": "C50",        # Neoplasia maligna da mama
        "leito_cnes": "51"       # Leito Oncologico
    },
    "QUIMIO_LEUCEMIA": {
        "proc_sia": "0304020119", # QUIMIOTERAPIA DA LEUCEMIA MIELOIDE AGUDA
        "cid_sih": "C92",        # Leucemia mieloide
        "leito_cnes": "51"       # Leito Oncologico
    }
}


def carregar_dados_reais_datasus(medicamento_proc: str, doenca_cid: str, recurso_cnes: str, ufs: list, start_date: str, end_date: str):
    """
    Carrega e processa dados reais do SIA, SIH e CNES para um período específico.
    """
    print("\n[LOG] Iniciando carregamento de dados reais do DataSUS...")
    datas = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='MS'))
    df_final = pd.DataFrame({'ds': datas})

    # --- 1. Carregar dados do SIA (Variável Alvo 'y') ---
    try:
        print(f"\n--- [SIA] Carregando para procedimento '{medicamento_proc}' ---")
        sia_db = SIA()
        sia_db.load()
        dfs_sia = []
        for ano in range(pd.to_datetime(start_date).year, pd.to_datetime(end_date).year + 1):
            for uf in ufs:
                files = sia_db.get_files(group='PA', uf=uf, year=ano)
                if files:
                    print(f"[DEBUG] Baixando {len(files)} arquivo(s) SIA/PA para {uf}/{ano}...")
                    parquet_set = sia_db.download(files)
                    if isinstance(parquet_set, list):
                         dfs_sia.extend([p.to_dataframe() for p in parquet_set])
                    elif hasattr(parquet_set, "to_dataframe"):
                         dfs_sia.append(parquet_set.to_dataframe())

        if not dfs_sia:
            print("[AVISO] Nenhum arquivo do SIA foi encontrado para o período/UF especificado.")
            df_final['y'] = 0
        else:
            df_sia_full = pd.concat(dfs_sia, ignore_index=True)
            print(f"[DEBUG] SIA: Total de {len(df_sia_full)} registros baixados.")

            df_sia_full['PA_CMP'] = pd.to_datetime(df_sia_full['PA_CMP'], format='%Y%m')
            df_medicamento = df_sia_full[df_sia_full['PA_PROC_ID'] == medicamento_proc].copy()
            print(f"[DEBUG] SIA: {len(df_medicamento)} registros encontrados para o procedimento {medicamento_proc}.")

            if not df_medicamento.empty:
                df_medicamento['PA_QTDAPR'] = pd.to_numeric(df_medicamento['PA_QTDAPR'], errors='coerce').fillna(0)
                demanda_mensal = df_medicamento.groupby(pd.Grouper(key='PA_CMP', freq='MS'))['PA_QTDAPR'].sum().rename('y').reset_index()
                demanda_mensal.rename(columns={'PA_CMP': 'ds'}, inplace=True)
                df_final = pd.merge(df_final, demanda_mensal, on='ds', how='left')
            else:
                df_final['y'] = 0

            print(f"  -> [OK] Dados do SIA processados.")

    except Exception as e:
        print(f"  -> [ERRO] Falha ao processar dados do SIA: {e}. Usando série zerada.")
        df_final['y'] = 0

    # --- 2. Carregar dados do SIH (Regressor 1) ---
    try:
        print(f"\n--- [SIH] Carregando para CID '{doenca_cid}' ---")
        sih_db = SIH()
        sih_db.load()
        dfs_sih = []
        for ano in range(pd.to_datetime(start_date).year, pd.to_datetime(end_date).year + 1):
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
            df_final['internacoes_relacionadas'] = 0
        else:
            df_sih_full = pd.concat(dfs_sih, ignore_index=True)
            print(f"[DEBUG] SIH: Total de {len(df_sih_full)} registros baixados.")

            df_sih_full['DT_INTER'] = pd.to_datetime(df_sih_full['DT_INTER'], errors='coerce')
            df_internacoes = df_sih_full[df_sih_full['DIAG_PRINC'].str.startswith(doenca_cid, na=False)]
            print(f"[DEBUG] SIH: {len(df_internacoes)} internações encontradas para o CID {doenca_cid}.")

            if not df_internacoes.empty:
                internacoes_mensal = df_internacoes.groupby(pd.Grouper(key='DT_INTER', freq='MS')).size().rename('internacoes_relacionadas').reset_index()
                internacoes_mensal.rename(columns={'DT_INTER': 'ds'}, inplace=True)
                df_final = pd.merge(df_final, internacoes_mensal, on='ds', how='left')
            else:
                df_final['internacoes_relacionadas'] = 0

            print(f"  -> [OK] Dados do SIH processados.")

    except Exception as e:
        print(f"  -> [ERRO] Falha ao processar dados do SIH: {e}. Usando série zerada.")
        df_final['internacoes_relacionadas'] = 0

    # --- 3. Carregar dados do CNES (Regressor 2) ---
    try:
        print(f"\n--- [CNES] Carregando para leitos tipo '{recurso_cnes}' ---")
        cnes_db = CNES()
        cnes_db.load(groups=['LT'])
        dfs_cnes = []
        for ano in range(pd.to_datetime(start_date).year, pd.to_datetime(end_date).year + 1):
             for mes in range(1, 13):
                for uf in ufs:
                    files = cnes_db.get_files(group='LT', uf=uf, year=ano, month=mes)
                    if files:
                        parquet_set = cnes_db.download(files)
                        if isinstance(parquet_set, list):
                            dfs_cnes.extend([p.to_dataframe() for p in parquet_set])
                        elif hasattr(parquet_set, "to_dataframe"):
                            dfs_cnes.append(parquet_set.to_dataframe())

        if not dfs_cnes:
            print("[AVISO] Nenhum arquivo do CNES foi encontrado para o período/UF especificado.")
            df_final['leitos_especializados'] = 0
        else:
            df_cnes_full = pd.concat(dfs_cnes, ignore_index=True)
            print(f"[DEBUG] CNES: Total de {len(df_cnes_full)} registros baixados.")

            if 'TP_LEITO' in df_cnes_full.columns:
                df_cnes_full['TP_LEITO'] = df_cnes_full['TP_LEITO'].astype(str).str.strip()
            else:
                 print("[AVISO] Coluna 'TP_LEITO' não encontrada nos dados do CNES.")

            df_cnes_full['COMPETEN'] = pd.to_datetime(df_cnes_full['COMPETEN'], format='%Y%m')
            df_leitos = df_cnes_full[df_cnes_full['TP_LEITO'] == recurso_cnes].copy()
            print(f"\n[DEBUG] CNES: {len(df_leitos)} registros de leitos encontrados para o tipo '{recurso_cnes}'.")

            if not df_leitos.empty:
                df_leitos['QT_EXIST'] = pd.to_numeric(df_leitos['QT_EXIST'], errors='coerce').fillna(0)
                leitos_mensal = df_leitos.groupby(pd.Grouper(key='COMPETEN', freq='MS'))['QT_EXIST'].sum().rename('leitos_especializados').reset_index()
                leitos_mensal.rename(columns={'COMPETEN': 'ds'}, inplace=True)
                df_final = pd.merge(df_final, leitos_mensal, on='ds', how='left')
            else:
                df_final['leitos_especializados'] = 0

            print(f"  -> [OK] Dados do CNES processados.")

    except Exception as e:
        print(f"  -> [ERRO] Falha ao processar dados do CNES: {e}. Usando série zerada.")
        df_final['leitos_especializados'] = 0

    print("\n[LOG] Consolidando DataFrame final...")

    cols_to_fill = ['y', 'internacoes_relacionadas', 'leitos_especializados']
    for col in cols_to_fill:
        if col in df_final.columns:
            df_final[col] = df_final[col].fillna(0)
        else:
            df_final[col] = 0

    df_final[cols_to_fill] = df_final[cols_to_fill].astype(int)

    print("[DEBUG] DataFrame final antes de retornar (amostra):")
    print(df_final.head())
    print("\n[LOG] Carregamento de dados reais concluído.")
    return df_final


def processar_previsao_demanda_medicamentos(medicamento_id: str, medicamento_config: dict, ufs: list, anos_historico: list, meses_previsao: int, dir_saida_previsao: Path):
    """
    Orquestra o processo de previsão para um único medicamento, utilizando sempre dados reais.
    """
    print(f"\n--- Processando Previsão para o Medicamento: {medicamento_id} ---")

    start_date = f"{min(anos_historico)}-01-01"
    end_date = f"{max(anos_historico)}-12-01"

    df_historico = carregar_dados_reais_datasus(
        medicamento_proc=medicamento_config['proc_sia'],
        doenca_cid=medicamento_config['cid_sih'],
        recurso_cnes=medicamento_config['leito_cnes'],
        ufs=ufs,
        start_date=start_date,
        end_date=end_date
    )

    if df_historico.empty:
        print(f"❌ ERRO CRÍTICO: DataFrame histórico está vazio para {medicamento_id}. Abortando previsão.")
        return

    if 'y' not in df_historico.columns or df_historico['y'].sum() == 0:
        print(f"❌ ERRO CRÍTICO: Nenhum dado de demanda (y) encontrado para o medicamento {medicamento_id} no período e UFs especificados.")
        print("   -> A previsão será abortada. Verifique os códigos do procedimento e os filtros no dicionário MEDICAMENTOS_CONFIG.")
        return

    print("\n[LOG] Treinando o modelo Prophet com parâmetros de regularização...")

    df_historico['floor'] = 0

    # --- CORREÇÃO APLICADA AQUI: Lógica de feriados removida ---
    modelo = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_prior_scale=5.0,
        growth='logistic'
    )

    modelo.add_seasonality(name='quarterly', period=91.25, fourier_order=4)

    df_historico['cap'] = df_historico['y'].max() * 1.5

    modelo.add_regressor('internacoes_relacionadas', prior_scale=0.5)
    modelo.add_regressor('leitos_especializados', prior_scale=0.5)

    print("[DEBUG] Amostra do DataFrame enviado para o treinamento do Prophet (com floor e cap):")
    print(df_historico.head())

    modelo.fit(df_historico)
    print("[LOG] Modelo treinado com sucesso.")

    print(f"\n[LOG] Gerando datas futuras para {meses_previsao} meses de previsão...")
    futuro = modelo.make_future_dataframe(periods=meses_previsao, freq='MS')

    futuro['cap'] = df_historico['cap'].iloc[0]
    futuro['floor'] = 0

    last_3m_internacoes = df_historico['internacoes_relacionadas'].tail(3).mean()
    last_3m_leitos = df_historico['leitos_especializados'].tail(3).mean()
    futuro['internacoes_relacionadas'] = last_3m_internacoes
    futuro['leitos_especializados'] = last_3m_leitos
    futuro.loc[futuro['ds'].isin(df_historico['ds']), ['internacoes_relacionadas', 'leitos_especializados']] = df_historico[['internacoes_relacionadas', 'leitos_especializados']].values

    print("[DEBUG] Amostra do DataFrame futuro com regressores preenchidos:")
    print(futuro.tail())

    print("\n[LOG] Realizando a previsão...")
    previsao = modelo.predict(futuro)
    print("[LOG] Previsão concluída.")

    dir_saida_previsao.mkdir(parents=True, exist_ok=True)
    ufs_str = '_'.join(ufs).lower()
    nome_arquivo_csv = f"previsao_demanda_{medicamento_id}_{ufs_str}.csv"
    caminho_csv = dir_saida_previsao / nome_arquivo_csv
    previsao[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'internacoes_relacionadas', 'leitos_especializados']].to_csv(
        caminho_csv, sep=';', encoding='utf-8-sig', index=False
    )
    print(f"✅ Previsão em CSV salva em: {caminho_csv}")

    fig1 = modelo.plot(previsao, xlabel='Data', ylabel=f'Demanda do Medicamento {medicamento_id}')
    ax1 = fig1.gca()
    ax1.set_title(f'Previsão de Demanda - {medicamento_id} (UFs: {", ".join(ufs)})', size=16)
    caminho_grafico1 = dir_saida_previsao / f"grafico_previsao_{medicamento_id}_{ufs_str}.png"
    fig1.savefig(caminho_grafico1, dpi=300)
    plt.close(fig1)
    print(f"📈 Gráfico de previsão salvo em: {caminho_grafico1}")

    fig2 = modelo.plot_components(previsao)
    caminho_grafico2 = dir_saida_previsao / f"grafico_componentes_{medicamento_id}_{ufs_str}.png"
    fig2.savefig(caminho_grafico2, dpi=300)
    plt.close(fig2)
    print(f"📊 Gráfico de componentes salvo em: {caminho_grafico2}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Executa a previsão de demanda para um ou mais medicamentos usando dados reais do DataSUS.")

    parser.add_argument("--medicamentos", nargs="+", default=["CONSULTA_MEDICA"],
                        help=f"Lista de nomes de medicamentos a prever. Válidos: {list(MEDICAMENTOS_CONFIG.keys())}")

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de siglas de UFs a processar. Ex: TO SP RJ")
    parser.add_argument("--anos", nargs="+", type=int, default=[2024, 2025], help="Anos de dados históricos a usar.")
    parser.add_argument("--meses_futuros", type=int, default=12, help="Número de meses a prever no futuro.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsoes", help="Diretório para salvar os resultados.")

    args = parser.parse_args()

    for med_nome in args.medicamentos:
        if med_nome in MEDICAMENTOS_CONFIG:
            print(f"\n\n{'='*80}\nINICIANDO PROCESSAMENTO PARA: {med_nome}\n{'='*80}")
            config = MEDICAMENTOS_CONFIG[med_nome]

            processar_previsao_demanda_medicamentos(
                medicamento_id=med_nome,
                medicamento_config=config,
                ufs=args.ufs,
                anos_historico=args.anos,
                meses_previsao=args.meses_futuros,
                dir_saida_previsao=Path(args.dir_saida)
            )
        else:
            print(f"\n⚠️ AVISO: Medicamento '{med_nome}' não encontrado na configuração. Pulando.")
            print(f"   -> Opções válidas são: {list(MEDICAMENTOS_CONFIG.keys())}")
