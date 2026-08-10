# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE SOBREVIVÊNCIA E FATORES DE RISCO PARA READMISSÃO HOSPITALAR
======================================================================
Este script implementa um pipeline de Análise de Sobrevivência para
investigar o tempo até a primeira readmissão hospitalar e identificar os
fatores de risco que mais encurtam esse tempo.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import joblib
import shap
import matplotlib.pyplot as plt
import seaborn as sns

from pysus.online_data.SIH import SIH
from pysus.online_data.CNES import CNES

from lifelines import CoxPHFitter, KaplanMeierFitter

def carregar_e_preparar_dados(ufs: list, anos: list):
    """
    Carrega dados do SIH e CNES e prepara para a análise de sobrevivência,
    criando as colunas de 'duração' e 'evento'.
    """
    print(f"\n--- [ETAPA 1] Carregando e preparando dados para {ufs}/{anos} ---")

    def _download_and_concat(db_instance, files_list):
        downloaded_items = db_instance.download(files_list)
        if isinstance(downloaded_items, list):
            return pd.concat([item.to_dataframe() for item in downloaded_items if hasattr(item, 'to_dataframe')], ignore_index=True)
        elif hasattr(downloaded_items, 'to_dataframe'):
            return downloaded_items.to_dataframe()
        return pd.DataFrame()

    df_sih, df_cnes = pd.DataFrame(), pd.DataFrame()

    # Carregar SIH
    try:
        print("[LOG] Carregando SIH..."); sih_db = SIH().load()
        files_sih = sih_db.get_files(group='RD', uf=ufs, year=anos)
        if files_sih:
            df_sih = _download_and_concat(sih_db, files_sih)
            if df_sih.empty: print(f"  -> Aviso: Nenhum dado SIH para {ufs}/{anos}.")
        else: print(f"  -> Aviso: Nenhum arquivo SIH encontrado para {ufs}/{anos}.")
    except Exception as e:
        print(f"❌ Erro ao carregar SIH: {e}"); return None

    # Carregar CNES
    try:
        print("[LOG] Carregando CNES..."); cnes_db = CNES().load()
        dfs_cnes_ano = []
        for ano in anos:
            files_cnes = cnes_db.get_files(group='ST', uf=ufs, year=ano, month=12)
            if files_cnes:
                df_ano = _download_and_concat(cnes_db, files_cnes)
                if not df_ano.empty:
                    df_ano['ANO_COMPETENCIA_CNES'] = ano # Adiciona ano para o join
                    dfs_cnes_ano.append(df_ano)
                else: print(f"  -> Aviso: Nenhum dado CNES (ST) para {ufs}/{ano}.")
            else: print(f"  -> Aviso: Nenhum arquivo CNES (ST) encontrado para {ufs}/{ano}.")
        if dfs_cnes_ano:
            df_cnes = pd.concat(dfs_cnes_ano, ignore_index=True)

    except Exception as e:
        print(f"❌ Erro ao carregar CNES: {e}"); return None

    if df_sih.empty or df_cnes.empty:
        print("❌ Uma ou ambas as bases de dados (SIH/CNES) estão vazias após o carregamento. Abortando."); return None

    print("[LOG] Preparando dados para análise de sobrevivência...")

    # 1. Criar pseudo-ID e ordenar internações
    df_sih['pseudo_id'] = df_sih['NASC'].astype(str) + '_' + df_sih['SEXO'].astype(str) + '_' + df_sih['MUNIC_RES'].astype(str)
    df_sih['DT_INTER'] = pd.to_datetime(df_sih['DT_INTER'], format='%Y%m%d', errors='coerce')
    df_sih['DT_SAIDA'] = pd.to_datetime(df_sih['DT_SAIDA'], format='%Y%m%d', errors='coerce')
    df_sih.dropna(subset=['DT_INTER', 'DT_SAIDA'], inplace=True)
    df_sih = df_sih.sort_values(by=['pseudo_id', 'DT_INTER'])

    # 2. Calcular o tempo até a próxima internação
    df_sih['proxima_internacao'] = df_sih.groupby('pseudo_id')['DT_INTER'].shift(-1)
    df_sih['dias_ate_readmissao'] = (df_sih['proxima_internacao'] - df_sih['DT_SAIDA']).dt.days

    # 3. Criar a variável de evento (censura)
    df_sih['ocorreu_readmissao'] = np.where(df_sih['dias_ate_readmissao'].notna(), 1, 0)

    # Para os pacientes não readmitidos, o tempo de observação é do início do estudo até sua última alta
    data_fim_estudo = pd.to_datetime(f"{max(anos)}-12-31")
    df_sih['dias_ate_censura'] = (data_fim_estudo - df_sih['DT_SAIDA']).dt.days

    # 4. Criar a coluna final de duração
    df_sih['duracao'] = df_sih['dias_ate_readmissao'].fillna(df_sih['dias_ate_censura'])
    df_sih = df_sih[df_sih['duracao'] > 0].copy()

    # 5. Juntar com CNES e selecionar features
    df_sih['ANO_CMPT'] = df_sih['DT_INTER'].dt.year
    df_sih['CNES'] = pd.to_numeric(df_sih['CNES'], errors='coerce').astype('Int64').astype(str)
    df_cnes['CNES'] = pd.to_numeric(df_cnes['CNES'], errors='coerce').astype('Int64').astype(str)
    df = pd.merge(df_sih, df_cnes,
                  left_on=['CNES', 'ANO_CMPT'],
                  right_on=['CNES', 'ANO_COMPETENCIA_CNES'],
                  how='left')

    features_modelo = [
        'duracao', 'ocorreu_readmissao', 'IDADE', 'SEXO', 'DIAS_PERM',
        'UTI_MES_TO', 'DIAG_PRINC', 'LEITHOSP', 'ATIVIDAD', 'TP_UNID', 'NAT_JUR', 'CAR_INT', 'MORTE' # Adicionando mais features
    ]
    df_final = df[[col for col in features_modelo if col in df.columns]].copy()

    # Limpeza final e tratamento de tipos
    for col in ['IDADE', 'DIAS_PERM', 'UTI_MES_TO', 'LEITHOSP']:
        df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
    df_final.dropna(inplace=True) # Remove linhas com nulos nas features numéricas cruciais

    print(f"✅ Dados preparados com {len(df_final)} internações válidas para a análise.")
    return df_final


def analisar_sobrevida_e_risco(df: pd.DataFrame, dir_saida: Path):
    """Treina um modelo de Cox, interpreta e visualiza os resultados."""
    print("\n--- [ETAPA 2] Treinando Modelo de Sobrevivência (Cox PH) ---")
    dir_saida.mkdir(parents=True, exist_ok=True)

    df_cox = df.copy()

    # --- CORREÇÃO APLICADA AQUI ---
    # 1. Pré-tratamento de categóricas: preenche nulos e converte para string
    categorical_cols_for_prep = ['SEXO', 'DIAG_PRINC', 'ATIVIDAD', 'TP_UNID', 'NAT_JUR', 'CAR_INT', 'MORTE']
    for col in categorical_cols_for_prep:
        if col in df_cox.columns:
            # Substitui NaNs ou outros valores problemáticos por 'IGNORADO' e garante que seja string
            df_cox[col] = df_cox[col].astype(str).replace({'nan': 'IGNORADO', 'None': 'IGNORADO'}).fillna('IGNORADO')

    # 2. Simplificação do DIAG_PRINC para capítulo (evita alta cardinalidade e nulos)
    if 'DIAG_PRINC' in df_cox.columns:
        df_cox['DIAG_PRINC_CAP'] = df_cox['DIAG_PRINC'].astype(str).str[0]
        # Garante que 'DIAG_PRINC_CAP' não tenha valores raros ou vazios
        # Remova capítulos que podem ser raros ou inespecíficos se causarem problemas de convergência
        # Ou agrupe os mais raros em 'OUTROS_CID'
        df_cox['DIAG_PRINC_CAP'] = df_cox['DIAG_PRINC_CAP'].replace({'nan': 'CID_IGNORADO'})
    else:
        df_cox['DIAG_PRINC_CAP'] = 'CID_IGNORADO' # Fallback se a coluna não existir

    # 3. Criação de dummies (one-hot encoding) para as categóricas
    # Remove as colunas originais que serão dummies, e também DIAG_PRINC
    cols_to_dummy = ['SEXO', 'DIAG_PRINC_CAP', 'ATIVIDAD', 'TP_UNID', 'NAT_JUR', 'CAR_INT', 'MORTE']
    cols_to_dummy = [col for col in cols_to_dummy if col in df_cox.columns] # Filtra só as existentes

    df_cox = pd.get_dummies(df_cox, columns=cols_to_dummy, drop_first=True, dtype=int)

    # Remove a coluna DIAG_PRINC original se ela ainda estiver lá
    if 'DIAG_PRINC' in df_cox.columns:
        df_cox = df_cox.drop(columns=['DIAG_PRINC'])

    # 4. Selecionar covariáveis finais
    # Exclua as colunas que não são features para o modelo (duração, evento, e as originais convertidas)
    covariates_to_exclude_from_final_list = ['duracao', 'ocorreu_readmissao', 'DIAG_PRINC'] + categorical_cols_for_prep # Exclui as originais de prep
    covariates = [col for col in df_cox.columns if col not in covariates_to_exclude_from_final_list]

    # TRATAMENTO CRUCIAL: Remover covariáveis com variância zero (constantes)
    final_covariates = []
    for col in covariates:
        if pd.api.types.is_numeric_dtype(df_cox[col]):
            if df_cox[col].std() > 0: # Variância maior que zero
                # Garante que não há nulos na coluna numérica final (fill com mediana/0 se necessário)
                if df_cox[col].isnull().any():
                    median_val = df_cox[col].median() if df_cox[col].dtype != int else 0 # Mediana para float, 0 para int
                    df_cox[col].fillna(median_val, inplace=True)
                final_covariates.append(col)
            else:
                print(f"AVISO: Covariável '{col}' removida por ter variância zero (constante).")
        else:
            # Colunas que não são numéricas/dummy devem ter sido excluídas ou convertidas antes
            print(f"AVISO: Covariável '{col}' removida por tipo inválido (não numérica/dummy após get_dummies).")

    if not final_covariates:
        print("❌ Erro: Nenhuma covariável válida para o modelo de Cox após o pré-processamento. Abortando.")
        return

    # Instanciar e treinar o modelo
    cph = CoxPHFitter()

    try:
        # Passa apenas as colunas válidas e sem variância zero para o fit
        cph.fit(df_cox[final_covariates + ['duracao', 'ocorreu_readmissao']],
                duration_col='duracao',
                event_col='ocorreu_readmissao',
                formula="+ ".join(final_covariates))
    except Exception as e:
        print(f"❌ Erro ao treinar o modelo de Cox: {e}")
        print("   -> Dica: Verifique a distribuição das suas variáveis e se há muita multicolinearidade.")
        print(f"   -> Covariáveis finais utilizadas: {final_covariates}")
        print(f"   -> Sumário de df_cox[final_covariates].describe():\n{df_cox[final_covariates].describe()}")
        return


    print("\n" + "="*80)
    print("--- RESULTADOS DO MODELO DE RISCOS PROPORCIONAIS DE COX ---")
    cph.print_summary()
    print("="*80)

    caminho_modelo = dir_saida / "modelo_cox_readmissao.joblib"
    joblib.dump(cph, caminho_modelo)
    print(f"\n💾 Modelo de sobrevivência Cox salvo em: {caminho_modelo}")


    # Visualização dos resultados
    # 1. Gráfico dos coeficientes (Hazard Ratios)
    plt.figure(figsize=(10, 8))
    cph.plot()
    plt.title("Fatores de Risco para Readmissão Hospitalar (Hazard Ratios)")
    caminho_fig1 = dir_saida / "coeficientes_risco_cox.png"
    plt.savefig(caminho_fig1, bbox_inches='tight')
    plt.close()
    print(f"\n📈 Gráfico de Hazard Ratios salvo em: {caminho_fig1}")

    # 2. Curvas de Sobrevivência para um fator de risco importante (ex: Uso de UTI)
    # Garante que 'UTI_MES_TO' exista e seja numérica
    if 'UTI_MES_TO' in df.columns: # Usa o df original, não df_cox, para ter o nome original
        df_plot = df[['duracao', 'ocorreu_readmissao', 'UTI_MES_TO']].copy()
        df_plot['USOU_UTI'] = pd.to_numeric(df_plot['UTI_MES_TO'], errors='coerce').fillna(0) > 0

        if df_plot['USOU_UTI'].nunique() > 1:
            plt.figure(figsize=(12, 7))
            ax = plt.subplot(111)

            for usou_uti, sub_df in df_plot.groupby('USOU_UTI'):
                kmf = KaplanMeierFitter()
                kmf.fit(sub_df['duracao'], sub_df['ocorreu_readmissao'], label=f"Usou UTI: {'Sim' if usou_uti else 'Não'}")
                kmf.plot_survival_function(ax=ax)

            plt.title("Curva de Sobrevida Livre de Readmissão (Uso de UTI)")
            plt.xlabel("Dias Após a Alta")
            plt.ylabel("Probabilidade de Estar Livre de Readmissão")
            plt.grid(True)
            caminho_fig2 = dir_saida / "curva_sobrevida_uti.png"
            plt.savefig(caminho_fig2)
            plt.close()
            print(f"📊 Gráfico de Curva de Sobrevida salvo em: {caminho_fig2}")
        else:
            print("⚠️ Coluna 'UTI_MES_TO' não tem variação suficiente para plotar curva de sobrevida por uso de UTI.")
    else:
        print("⚠️ Coluna 'UTI_MES_TO' não encontrada para plotar curva de sobrevida por uso de UTI.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa uma análise de sobrevivência para o tempo até a readmissão hospitalar.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022, 2023], help="Anos de dados históricos a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/analise_sobrevida_readmissao", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    df_final = carregar_e_preparar_dados(ufs=args.ufs, anos=args.anos)

    if df_final is not None and not df_final.empty:
        analisar_sobrevida_e_risco(df_final, Path(args.dir_saida))
        print("\n" + "="*80)
        print("🎉 PIPELINE DE ANÁLISE DE SOBREVIVÊNCIA CONCLUÍDO! 🎉")
        print("="*80)
