# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE SEQUÊNCIA DE EVENTOS E JORNADAS DE PACIENTES
======================================================================
Este script implementa um pipeline de engenharia de dados para:
1. Carregar dados otimizados de SIH e SIA.
2. Criar um identificador de paciente consistente e harmonizado entre as bases.
3. Extrair as sequências de atendimentos ambulatoriais que antecedem
   uma internação para uma coorte de pacientes.
4. Analisar e contar as jornadas (sequências) mais frequentes.
"""

import pandas as pd
from pathlib import Path
import argparse
import numpy as np

def carregar_dados_otimizados(caminho_sih: Path, caminho_sia: Path):
    """Carrega os arquivos Parquet otimizados do SIH e SIA."""
    print("\n--- [ETAPA 1] Carregando dados otimizados ---")
    try:
        df_sih = pd.read_parquet(caminho_sih)
        df_sia = pd.read_parquet(caminho_sia)
        print(f"✅ Dados carregados. SIH: {len(df_sih)} registros, SIA: {len(df_sia)} registros.")
        return df_sih, df_sia
    except FileNotFoundError as e:
        print(f"❌ ERRO: Arquivo otimizado não encontrado: {e}")
        print("   -> Por favor, execute o 'pipeline_doencas_cronicas.py' para gerar os arquivos otimizados.")
        return None, None

def criar_ids_de_paciente(df_sih: pd.DataFrame, df_sia: pd.DataFrame):
    """
    Cria uma coluna 'ID_PACIENTE' em cada DataFrame usando um pseudo-ID
    demográfico consistente e HARMONIZADO.
    """
    print("\n--- [ETAPA 1.5] Criando e Harmonizando Identificadores de Paciente ---")

    # --- Harmonização para o SIH ---
    sih_id_cols = ['NASC', 'SEXO', 'MUNIC_RES']
    if not all(col in df_sih.columns for col in sih_id_cols):
        print(f"❌ Erro: Colunas necessárias para ID do SIH não encontradas: {sih_id_cols}")
        return None, None

    df_sih_id = df_sih[sih_id_cols].copy()

    # ==========================================================
    # --- CORREÇÃO APLICADA AQUI (SIH) ---
    # Usa apenas os 4 primeiros dígitos de 'NASC' para obter o ANO
    df_sih_id['ANO_NASC'] = df_sih_id['NASC'].astype(str).str[:4]
    # ==========================================================

    df_sih_id['SEXO_HARM'] = df_sih_id['SEXO'].astype(str)
    df_sih_id['MUN_RES_HARM'] = df_sih_id['MUNIC_RES'].astype(str).str[:6]
    df_sih['ID_PACIENTE'] = df_sih_id['ANO_NASC'] + '_' + df_sih_id['SEXO_HARM'] + '_' + df_sih_id['MUN_RES_HARM']

    # --- Harmonização para o SIA ---
    sia_id_cols = ['PA_DOCORIG', 'PA_IDADE', 'PA_SEXO', 'PA_MUNPCN', 'PA_CMP']
    if not all(col in df_sia.columns for col in sia_id_cols):
        print(f"❌ Erro: Colunas necessárias para ID do SIA não encontradas: {sia_id_cols}")
        return None, None

    df_sia_ind = df_sia[df_sia['PA_DOCORIG'].isin(['I', 'P', 'S', 'A', 'R'])].copy()

    df_sia_ind['ANO_ATENDIMENTO'] = pd.to_datetime(df_sia_ind['PA_CMP'], format='%Y%m', errors='coerce').dt.year
    df_sia_ind['ANO_NASC'] = (df_sia_ind['ANO_ATENDIMENTO'] - pd.to_numeric(df_sia_ind['PA_IDADE'], errors='coerce')).astype('Int64').astype(str).str.replace('.0','')

    sexo_map = {'M': '1', 'F': '3'}
    df_sia_ind['SEXO_HARM'] = df_sia_ind['PA_SEXO'].map(sexo_map).fillna('0')
    df_sia_ind['MUN_RES_HARM'] = df_sia_ind['PA_MUNPCN'].astype(str).str[:6]

    df_sia_ind['ID_PACIENTE'] = df_sia_ind['ANO_NASC'] + '_' + df_sia_ind['SEXO_HARM'] + '_' + df_sia_ind['MUN_RES_HARM']

    df_sia = df_sia.merge(df_sia_ind[['ID_PACIENTE']], left_index=True, right_index=True, how='left')

    df_sih.dropna(subset=['ID_PACIENTE'], inplace=True)

    print("✅ Coluna 'ID_PACIENTE' criada e harmonizada em ambas as bases.")
    return df_sih, df_sia

# (O restante do script, como as funções extrair_sequencias e analisar_frequencia, permanecem inalterados)
def extrair_sequencias_pre_evento(df_sih: pd.DataFrame, df_sia: pd.DataFrame, cid_coorte: str, cid_evento: str):
    print(f"\n--- [ETAPA 2] Extraindo sequências pré-evento (CID: {cid_evento}) ---")
    df_sih['DATA_EVENTO'] = pd.to_datetime(df_sih['DT_INTER'], format='%Y%m%d', errors='coerce')
    df_sia['DATA_EVENTO'] = pd.to_datetime(df_sia['PA_CMP'], format='%Y%m', errors='coerce')
    id_paciente = 'ID_PACIENTE'
    pacientes_sih = set(df_sih[df_sih['DIAG_PRINC'].astype(str).str.startswith(cid_coorte, na=False)][id_paciente].dropna())
    pacientes_sia = set(df_sia[df_sia['PA_CIDPRI'].astype(str).str.startswith(cid_coorte, na=False)][id_paciente].dropna())
    pacientes_coorte = pacientes_sih | pacientes_sia
    print(f"[LOG] Coorte identificada: {len(pacientes_coorte)} pacientes únicos com diagnóstico de '{cid_coorte}'.")
    df_sih_evento = df_sih[
        df_sih[id_paciente].isin(pacientes_coorte) &
        df_sih['DIAG_PRINC'].astype(str).str.startswith(cid_evento, na=False)
    ].sort_values('DATA_EVENTO').drop_duplicates(subset=id_paciente, keep='first')
    print(f"[LOG] {len(df_sih_evento)} pacientes da coorte tiveram o evento-desfecho (internação por '{cid_evento}').")
    sequencias_extraidas = []
    total_pacientes = len(df_sih_evento)
    for i, row in enumerate(df_sih_evento.itertuples()):
        if (i + 1) % 100 == 0:
            print(f"  -> Processando paciente {i+1}/{total_pacientes}...")
        paciente_id_val = getattr(row, id_paciente)
        data_evento = getattr(row, 'DATA_EVENTO')
        data_inicio_historico = data_evento - pd.DateOffset(months=12)
        hist_sia = df_sia[
            (df_sia[id_paciente] == paciente_id_val) &
            (df_sia['DATA_EVENTO'] >= data_inicio_historico) &
            (df_sia['DATA_EVENTO'] < data_evento)
        ].sort_values('DATA_EVENTO')
        if not hist_sia.empty:
            sequencia = hist_sia['PA_PROC_ID'].tolist()
            sequencias_extraidas.append({
                'ID_PACIENTE': paciente_id_val,
                'SEQUENCIA': sequencia
            })
    df_sequencias = pd.DataFrame(sequencias_extraidas)
    print(f"✅ Sequências de eventos extraídas para {len(df_sequencias)} pacientes.")
    return df_sequencias

def analisar_frequencia_sequencias(df_sequencias: pd.DataFrame):
    print("\n--- [ETAPA 3] Analisando a frequência das jornadas ---")
    if df_sequencias.empty:
        print("  -> Nenhum dado de sequência para analisar."); return pd.DataFrame()
    df_sequencias['SEQUENCIA_TUPLE'] = df_sequencias['SEQUENCIA'].apply(tuple)
    contagem = df_sequencias['SEQUENCIA_TUPLE'].value_counts().reset_index()
    contagem.columns = ['JORNADA_PACIENTE', 'FREQUENCIA']
    print(f"✅ Análise de frequência concluída. {len(contagem)} jornadas únicas encontradas.")
    return contagem

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o pipeline de análise de sequência de eventos para pacientes crônicos.")
    parser.add_argument("--sih-parquet", type=str, required=True, help="Caminho para o arquivo Parquet otimizado do SIH.")
    parser.add_argument("--sia-parquet", type=str, required=True, help="Caminho para o arquivo Parquet otimizado do SIA.")
    parser.add_argument("--cid-coorte", type=str, default="I50", help="CID-10 para definir a coorte de pacientes crônicos.")
    parser.add_argument("--cid-evento", type=str, default="I50", help="CID-10 do evento-desfecho (internação) a ser analisado.")
    parser.add_argument("--dir-saida", type=str, default="outputs/analise_sequencias", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    df_sih, df_sia = carregar_dados_otimizados(Path(args.sih_parquet), Path(args.sia_parquet))
    if df_sih is not None and df_sia is not None:
        df_sih_linked, df_sia_linked = criar_ids_de_paciente(df_sih, df_sia)
        if df_sih_linked is not None and df_sia_linked is not None:
            df_sequencias = extrair_sequencias_pre_evento(df_sih_linked, df_sia_linked, args.cid_coorte, args.cid_evento)
            if not df_sequencias.empty:
                df_frequencia = analisar_frequencia_sequencias(df_sequencias)
                output_dir = Path(args.dir_saida)
                output_dir.mkdir(parents=True, exist_ok=True)
                caminho_csv = output_dir / f"sequencias_frequentes_{args.cid_coorte}.csv"
                df_frequencia.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
                print(f"\n📄 Arquivo com as jornadas mais frequentes salvo em: '{caminho_csv}'")
                print("\n--- Amostra das 10 Jornadas Mais Comuns ---")
                print(df_frequencia.head(10))
                print("\n" + "="*80)
                print("🎉 PIPELINE DE ANÁLISE DE SEQUÊNCIAS CONCLUÍDO! 🎉")
                print("="*80)
