# -*- coding: utf-8 -*-
"""
======================================================================
  PIPELINE DE ALOCAÇÃO DE RECURSOS PARA ATENÇÃO PRIMÁRIA À SAÚDE (APS)
======================================================================
Este script cria um Índice de Priorização de Investimento em APS para
identificar os municípios que apresentam a combinação mais crítica de
alta necessidade de saúde e baixa oferta de serviços.

As dimensões e indicadores para o cálculo do índice são carregados a
partir de um arquivo de configuração JSON.
"""

import pandas as pd
from pathlib import Path
import argparse
import numpy as np
import json # Importa a biblioteca JSON
from sklearn.preprocessing import MinMaxScaler

def carregar_e_integrar_paineis(caminho_indicadores: Path, caminho_geo_sobrevida: Path, ano: int):
    """Carrega e junta os painéis de dados necessários."""
    print("\n--- [ETAPA 1] Carregando e integrando painéis de dados ---")
    try:
        df_indicadores = pd.read_csv(caminho_indicadores, sep=';', dtype={'cod_mun_ibge_6': str})
        # Adicionado low_memory=False para suprimir o DtypeWarning
        df_geo = pd.read_csv(caminho_geo_sobrevida, sep=';', dtype={'CODMUNRES': str}, low_memory=False)
        print("✅ Painéis de dados carregados com sucesso.")
    except FileNotFoundError as e:
        print(f"❌ ERRO: Arquivo não encontrado: {e}")
        print("   -> Certifique-se de que os scripts 'integrar_indicadores.py' e 'analise_risco_geografico.py' foram executados.")
        return None

    # Filtra para o ano de interesse
    df_indicadores = df_indicadores[df_indicadores['ANO'] == ano].copy()

    # Seleciona e renomeia colunas do painel geográfico para evitar duplicatas
    df_geo_slim = df_geo[['CODMUNRES', 'ivs']].rename(columns={'ivs': 'IVS_TOTAL'})
    df_geo_slim.drop_duplicates(subset=['CODMUNRES'], inplace=True)

    # Junta as duas bases de dados
    df_final = pd.merge(df_indicadores, df_geo_slim,
                        left_on='cod_mun_ibge_6', right_on='CODMUNRES',
                        how='left')

    print(f"✅ Painel de dados final integrado com {len(df_final)} municípios.")
    return df_final

def calcular_indice_priorizacao(df: pd.DataFrame, dimensoes: dict):
    """Normaliza indicadores e calcula o Índice de Priorização com base nas dimensões fornecidas."""
    print("\n--- [ETAPA 2] Calculando o Índice de Priorização de Investimento ---")

    df_scores = df[['cod_mun_ibge_6', 'municipio', 'UF', 'populacao']].copy()
    scaler = MinMaxScaler(feature_range=(0, 100))

    for dim_nome, indicadores in dimensoes.items():
        print(f"  -> Processando Dimensão: {dim_nome}")

        df_dim_scores = pd.DataFrame(index=df.index)

        for indicador, polaridade in indicadores.items():
            if indicador not in df.columns:
                print(f"     -> ⚠️ Aviso: Indicador '{indicador}' não encontrado. Pulando.")
                continue

            # Lógica de normalização robusta
            coluna_original = df[indicador].replace([np.inf, -np.inf], np.nan)
            coluna_para_scaler = coluna_original.dropna().to_frame()

            if not coluna_para_scaler.empty:
                scaled_values = scaler.fit_transform(coluna_para_scaler)
                df[f'{indicador}_norm'] = pd.Series(scaled_values.flatten(), index=coluna_para_scaler.index)

                if polaridade == 'low':
                    # Inverte a escala para indicadores onde "menor é pior"
                    df_dim_scores[f'{indicador}_score'] = 100 - df[f'{indicador}_norm']
                else:
                    # Mantém a escala para indicadores onde "maior é pior"
                    df_dim_scores[f'{indicador}_score'] = df[f'{indicador}_norm']

        # O score da dimensão é a média dos scores dos seus indicadores
        if not df_dim_scores.empty:
            df_scores[f'SCORE_{dim_nome}'] = df_dim_scores.mean(axis=1)

    # Preenche possíveis NaNs nos scores com a mediana, para robustez
    for col in df_scores.columns:
        if col.startswith('SCORE_'):
            df_scores[col].fillna(df_scores[col].median(), inplace=True)

    # Calcular o Índice de Priorização Final
    score_cols = [col for col in df_scores.columns if col.startswith('SCORE_')]
    df_scores['INDICE_PRIORIZACAO_FINAL'] = df_scores[score_cols].mean(axis=1)

    df_scores.sort_values('INDICE_PRIORIZACAO_FINAL', ascending=False, inplace=True)

    print("✅ Índice de Priorização calculado com sucesso.")
    return df_scores

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera um ranking de municípios para priorização de investimento em Atenção Primária.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--indicadores-csv", type=str, required=True, help="Caminho para o painel de indicadores gerado por 'integrar_indicadores.py'.")
    parser.add_argument("--geo-csv", type=str, required=True, help="Caminho para o painel de dados geográfico gerado por 'analise_risco_geografico.py'.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de análise para filtrar os dados.")
    parser.add_argument("--dir_saida", type=str, default="outputs/planejamento_aps", help="Diretório para salvar o relatório de priorização.")

    parser.add_argument(
        "--dimensoes-arquivo-json",
        type=str,
        default="config/dimensoes_padrao.json", # Define um caminho padrão para o arquivo
        help="Caminho para o arquivo .json que define as dimensões, indicadores e polaridades."
    )

    args = parser.parse_args()

    # Tenta carregar as dimensões a partir do arquivo JSON
    caminho_dimensoes = Path(args.dimensoes_arquivo_json)
    try:
        with open(caminho_dimensoes, 'r', encoding='utf-8') as f:
            dimensoes_customizadas = json.load(f)
        print(f"\n[LOG] Utilizando dimensões do arquivo: '{caminho_dimensoes}'")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"\n❌ ERRO: Não foi possível carregar ou decodificar o arquivo JSON de dimensões: {e}")
        print("      -> Certifique-se de que o caminho está correto e o JSON é válido.")
        exit() # Encerra o script se a configuração não puder ser carregada

    # Pipeline
    df_integrado = carregar_e_integrar_paineis(Path(args.indicadores_csv), Path(args.geo_csv), args.ano)

    if df_integrado is not None and not df_integrado.empty:
        df_ranking = calcular_indice_priorizacao(df_integrado, dimensoes_customizadas)

        if not df_ranking.empty:
            output_dir = Path(args.dir_saida)
            output_dir.mkdir(parents=True, exist_ok=True)

            ufs_str = '-'.join(df_ranking['UF'].dropna().unique()).lower()
            nome_arquivo = f"ranking_priorizacao_aps_{ufs_str}_{args.ano}.csv"
            caminho_csv = output_dir / nome_arquivo

            df_ranking.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig', decimal=',')

            print(f"\n📄 Relatório de priorização salvo em: '{caminho_csv}'")
            print("\n--- Amostra do Top 10 Municípios Prioritários ---")
            print(df_ranking.head(10))

            print("\n" + "="*80)
            print("🎉 PIPELINE DE ALOCAÇÃO DE RECURSOS CONCLUÍDO! 🎉")
            print("="*80)
