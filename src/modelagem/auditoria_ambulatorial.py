# -*- coding: utf-8 -*-
"""
======================================================================
  PIPELINE DE AUDITORIA INTELIGENTE EM PRODUÇÃO AMBULATORIAL (SIA)
======================================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse

from pysus.online_data.SIA import SIA
from pysus.online_data.CNES import CNES

def carregar_e_integrar_dados(ufs: list, anos: list):
    """Carrega dados do SIA e CNES e os integra em um único DataFrame."""
    print(f"\n--- [ETAPA 1] Carregando e integrando dados para {ufs}/{anos} ---")

    # Carregar SIA
    try:
        print("[LOG] Carregando dados do SIA...")
        sia_db = SIA().load()
        files_sia = sia_db.get_files(group='PA', uf=ufs, year=anos)
        downloaded_sia = sia_db.download(files_sia)

        if isinstance(downloaded_sia, list):
            df_sia = pd.concat([p.to_dataframe() for p in downloaded_sia], ignore_index=True)
        elif hasattr(downloaded_sia, "to_dataframe"):
            df_sia = downloaded_sia.to_dataframe()
        else:
            raise TypeError("SIA download result is not a DataFrame or list of DataFrames.")
    except Exception as e:
        print(f"❌ Erro ao carregar SIA: {e}"); return None

    # Carregar CNES
    try:
        print("[LOG] Carregando dados do CNES...")
        cnes_db = CNES().load()
        dfs_cnes_ano = []
        for ano in anos:
            files_cnes = cnes_db.get_files(group='ST', uf=ufs, year=ano, month=12)
            if not files_cnes:
                print(f"  -> Aviso: Nenhum arquivo CNES/ST encontrado para {ufs}/{ano}-12.")
                continue

            downloaded_cnes = cnes_db.download(files_cnes)

            # --- CORREÇÃO APLICADA AQUI ---
            # Normaliza a saída do download para uma lista de DataFrames
            if isinstance(downloaded_cnes, list):
                df_ano = pd.concat([f.to_dataframe() for f in downloaded_cnes], ignore_index=True)
            elif hasattr(downloaded_cnes, "to_dataframe"):
                df_ano = downloaded_cnes.to_dataframe()
            else:
                raise TypeError(f"CNES download result for {ufs}/{ano}-12 is not a DataFrame or list of DataFrames.")
            # --- FIM DA CORREÇÃO ---

            df_ano['ANO_COMPETENCIA_CNES'] = ano
            dfs_cnes_ano.append(df_ano)

        if dfs_cnes_ano:
            df_cnes = pd.concat(dfs_cnes_ano, ignore_index=True)
        else:
            print("  -> Aviso: Nenhum dado do CNES pôde ser carregado.")
            df_cnes = pd.DataFrame() # Garante um DataFrame vazio se não houver dados
    except Exception as e:
        print(f"❌ Erro ao carregar CNES: {e}"); return None

    # Integração
    if df_cnes.empty:
        print("❌ Erro: DataFrame do CNES está vazio. Não é possível integrar. Abortando.")
        return None

    df_sia['ANO_CMPT'] = pd.to_datetime(df_sia['PA_CMP'], format='%Y%m').dt.year
    df_sia['PA_CODUNI'] = pd.to_numeric(df_sia['PA_CODUNI'], errors='coerce').astype('Int64').astype(str)
    df_cnes['CNES'] = pd.to_numeric(df_cnes['CNES'], errors='coerce').astype('Int64').astype(str)

    df_integrado = pd.merge(df_sia, df_cnes,
                            left_on=['PA_CODUNI', 'ANO_CMPT'],
                            right_on=['CNES', 'ANO_COMPETENCIA_CNES'],
                            how='left')

    print(f"✅ Dados integrados com sucesso. Total de {len(df_integrado)} registros.")
    return df_integrado

def auditoria_baseada_em_regras(df: pd.DataFrame):
    """Aplica uma série de regras de negócio para encontrar inconsistências."""
    print("\n--- [ETAPA 2] Executando Auditoria Baseada em Regras ---")
    alertas = []

    # REGRA 1: Procedimentos de alta complexidade em locais inadequados
    procedimentos_alta_complexidade = ['0304020119'] # Ex: QUIMIOTERAPIA DA LEUCEMIA
    unidades_atencao_basica = ['01', '02', '15'] # Posto de Saúde, UBS, Unidade Mista

    # Garante que as colunas existam e que TP_UNID seja string
    if 'PA_PROC_ID' in df.columns and 'TP_UNID' in df.columns:
        df['TP_UNID'] = df['TP_UNID'].astype(str) # Garante que TP_UNID seja string
        df_alerta1 = df[
            df['PA_PROC_ID'].isin(procedimentos_alta_complexidade) &
            df['TP_UNID'].isin(unidades_atencao_basica)
        ].copy()
        if not df_alerta1.empty:
            df_alerta1['MOTIVO_ALERTA'] = "Procedimento de alta complexidade em unidade de atenção básica"
            alertas.append(df_alerta1)
            print(f"  -> {len(df_alerta1)} alertas encontrados para [Regra 1: Alta Complexidade em Local Inadequado]")
    else:
        print("  -> Aviso: Colunas para Regra 1 (PA_PROC_ID ou TP_UNID) não encontradas.")


    # REGRA 2: Incompatibilidade de procedimento vs. sexo
    procedimentos_masculinos = ['0409010118'] # Ex: VASECTOMIA
    procedimentos_femininos = ['0409060042']  # Ex: PARTO CESARIANO

    if 'PA_PROC_ID' in df.columns and 'PA_SEXO' in df.columns:
        df_alerta2_m = df[(df['PA_PROC_ID'].isin(procedimentos_masculinos)) & (df['PA_SEXO'] == 'F')].copy()
        df_alerta2_f = df[(df['PA_PROC_ID'].isin(procedimentos_femininos)) & (df['PA_SEXO'] == 'M')].copy()
        if not df_alerta2_m.empty or not df_alerta2_f.empty:
            df_alerta2 = pd.concat([df_alerta2_m, df_alerta2_f], ignore_index=True)
            df_alerta2['MOTIVO_ALERTA'] = "Procedimento incompatível com o sexo do paciente"
            alertas.append(df_alerta2)
            print(f"  -> {len(df_alerta2)} alertas encontrados para [Regra 2: Incompatibilidade Sexo vs. Procedimento]")
    else:
        print("  -> Aviso: Colunas para Regra 2 (PA_PROC_ID ou PA_SEXO) não encontradas.")


    if not alertas:
        print("  -> Nenhuma inconsistência encontrada nas regras.")
        return pd.DataFrame()

    df_alertas_regras = pd.concat(alertas, ignore_index=True)
    return df_alertas_regras


def auditoria_estatistica_volume(df: pd.DataFrame, z_score_threshold: float = 3.5):
    """Usa o Z-score para encontrar volumes de produção anormalmente altos."""
    print(f"\n--- [ETAPA 3] Executando Auditoria Estatística de Volume (Z-score > {z_score_threshold}) ---")

    if 'PA_QTDAPR' not in df.columns or 'PA_PROC_ID' not in df.columns:
        print("  -> Aviso: Colunas 'PA_QTDAPR' ou 'PA_PROC_ID' não encontradas para auditoria estatística.")
        return pd.DataFrame()

    df['PA_QTDAPR'] = pd.to_numeric(df['PA_QTDAPR'], errors='coerce')
    df_filtrado_qnt = df.dropna(subset=['PA_QTDAPR']).copy()

    if df_filtrado_qnt.empty:
        print("  -> Aviso: Nenhum dado válido para 'PA_QTDAPR' após limpeza.")
        return pd.DataFrame()

    # Foca nos 100 procedimentos mais comuns para performance
    top_100_procs = df_filtrado_qnt['PA_PROC_ID'].value_counts().nlargest(100).index
    df_filtrado = df_filtrado_qnt[df_filtrado_qnt['PA_PROC_ID'].isin(top_100_procs)].copy()

    if df_filtrado.empty:
        print("  -> Aviso: Nenhum dos 100 principais procedimentos encontrado após filtragem.")
        return pd.DataFrame()


    stats_proc = df_filtrado.groupby('PA_PROC_ID')['PA_QTDAPR'].agg(['mean', 'std']).reset_index()

    df_com_stats = pd.merge(df_filtrado, stats_proc, on='PA_PROC_ID', how='left')

    df_com_stats['z_score'] = (df_com_stats['PA_QTDAPR'] - df_com_stats['mean']) / (df_com_stats['std'] + 1e-6) # Adiciona um pequeno valor para evitar divisão por zero

    df_outliers = df_com_stats[df_com_stats['z_score'] > z_score_threshold].copy()
    df_outliers['MOTIVO_ALERTA'] = "Volume de produção estatisticamente anômalo (Z-score alto)"

    print(f"  -> {len(df_outliers)} alertas de outliers estatísticos encontrados.")
    return df_outliers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa uma auditoria inteligente na produção ambulatorial (SIA).")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2023], help="Anos de dados históricos a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/auditoria_ambulatorial", help="Diretório para salvar o relatório.")
    args = parser.parse_args()

    # 1. Carregar e integrar os dados
    df_integrado = carregar_e_integrar_dados(ufs=args.ufs, anos=args.anos)

    if df_integrado is not None and not df_integrado.empty:
        # 2. Executar as auditorias
        df_alertas_regras = auditoria_baseada_em_regras(df_integrado)
        df_alertas_estatisticos = auditoria_estatistica_volume(df_integrado)

        # 3. Consolidar e salvar o relatório
        colunas_relatorio = [
            'PA_CMP', 'UF', 'NO_FANTASIA', 'PA_CODUNI', 'PA_PROC_ID',
            'PA_QTDAPR', 'PA_VALAPR', 'MOTIVO_ALERTA'
        ]

        # Garante que os DataFrames de alertas não estejam vazios antes de concatenar
        list_to_concat = []
        if not df_alertas_regras.empty:
            list_to_concat.append(df_alertas_regras)
        if not df_alertas_estatisticos.empty:
            list_to_concat.append(df_alertas_estatisticos)

        if list_to_concat:
            df_relatorio_final = pd.concat(list_to_concat, ignore_index=True)
            # Filtra e reordena para o relatório final
            df_relatorio_final = df_relatorio_final[[col for col in colunas_relatorio if col in df_relatorio_final.columns]]

            output_dir = Path(args.dir_saida)
            output_dir.mkdir(parents=True, exist_ok=True)
            caminho_csv = output_dir / "relatorio_auditoria.csv"

            df_relatorio_final.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')

            print(f"\n📄 Relatório de auditoria consolidado salvo em: '{caminho_csv}'")
            print("\n--- Amostra dos Alertas Gerados ---")
            print(df_relatorio_final.head(10))
        else:
            print("\n✅ Nenhuma anomalia encontrada que corresponda aos critérios de auditoria.")

        print("\n" + "="*80)
        print("🎉 PIPELINE DE AUDITORIA CONCLUÍDO! 🎉")
        print("="*80)
    else:
        print("\n❌ Não foi possível carregar os dados integrados. Pipeline de auditoria não executado.")
