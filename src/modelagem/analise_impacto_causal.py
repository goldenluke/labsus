# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE IMPACTO CAUSAL DE INTERVENÇÕES EM SAÚDE
======================================================================
Este script utiliza a metodologia de Escore de Propensão (Propensity
Score Matching - PSM) para estimar o efeito causal de uma intervenção
(ex: pré-natal adequado) sobre um desfecho de saúde (ex: mortalidade infantil).

O objetivo é ir além da correlação e se aproximar de uma resposta para
a pergunta "A intervenção X realmente causa a redução no desfecho Y?".
"""

import pandas as pd
from pathlib import Path
import argparse

# Bibliotecas para inferência causal e modelagem
from causalinference import CausalModel
import statsmodels.api as sm

def carregar_e_preparar_dados(caminho_dados: Path):
    """
    Carrega o painel de dados, seleciona as variáveis e prepara para a análise causal.
    """
    print("\n--- [ETAPA 1] Carregando e preparando dados para análise causal ---")

    try:
        df = pd.read_csv(caminho_dados, sep=';')
        print(f"✅ Dados carregados de '{caminho_dados.name}'. Shape: {df.shape}")
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo de dados não encontrado em '{caminho_dados}'.")
        print("   -> Execute 'analise_risco_geografico.py' primeiro para gerar o painel de dados completo.")
        return None

    # 1. Definir a Intervenção (Tratamento)
    # Intervenção: Pré-natal adequado (7 ou mais consultas)
    # A variável CONSPRENAT do SINASC é categórica: 1(Nenhuma), 2(1-3), 3(4-6), 4(7+)
    df['PRENATAL_ADEQUADO'] = (pd.to_numeric(df['CONSPRENAT'], errors='coerce') == 4).astype(int)

    # 2. Definir o Desfecho
    # O desfecho já existe: OBITO_INFANTIL (0 ou 1)

    # 3. Definir as Variáveis de Confusão (Covariáveis)
    # Fatores que podem influenciar tanto o acesso ao pré-natal quanto o risco de óbito.
    confounders = [
        'IDADEMAE', 'ESCMAE2010', 'RACACORMAE', 'QTDFILVIVO', 'QTDFILMORT',
        'PARTO', 'GRAVIDEZ', 'ivs' # Incluindo a vulnerabilidade social
    ]

    # 4. Selecionar e limpar o dataset final
    colunas_necessarias = ['OBITO_INFANTIL', 'PRENATAL_ADEQUADO'] + confounders
    df_causal = df[colunas_necessarias].copy()

    for col in df_causal.columns:
        df_causal[col] = pd.to_numeric(df_causal[col], errors='coerce')

    initial_rows = len(df_causal)
    df_causal.dropna(inplace=True)
    print(f"[LOG] {initial_rows - len(df_causal)} registros removidos por dados ausentes.")
    print(f"✅ Dados preparados com {len(df_causal)} observações completas.")

    return df_causal

def analisar_impacto_causal(df: pd.DataFrame):
    """
    Estima o escore de propensão, realiza o pareamento e calcula o efeito causal.
    """
    print("\n--- [ETAPA 2] Estimando o Efeito Causal com Escore de Propensão ---")

    # 1. Separar os dados em Desfecho (Y), Tratamento (D) e Covariáveis (X)
    y = df['OBITO_INFANTIL'].values
    D = df['PRENATAL_ADEQUADO'].values
    X = df.drop(columns=['OBITO_INFANTIL', 'PRENATAL_ADEQUADO']).values

    # 2. Instanciar o Modelo Causal
    # A biblioteca 'causalinference' fará todo o trabalho pesado
    causal = CausalModel(Y=y, D=D, X=X)

    # 3. Estimar o Escore de Propensão
    # O modelo treina internamente uma regressão logística para prever D a partir de X
    print("[LOG] Estimando os escores de propensão...")
    causal.est_propensity_s()

    # 4. Realizar o Pareamento (Matching)
    # O método 'match_s' encontra os "gêmeos estatísticos"
    print("[LOG] Realizando o pareamento por escore de propensão...")
    causal.match_s()

    # 5. Estimar o Efeito Causal
    print("[LOG] Estimando o efeito do tratamento nos tratados (ATT)...")
    causal.est_effects()

    # 6. Apresentar os Resultados
    print("\n" + "="*80)
    print("--- RESULTADOS DA ANÁLISE DE IMPACTO CAUSAL ---")
    print("="*80)

    print("\nResumo dos Resultados do Escore de Propensão e Pareamento:")
    # A biblioteca fornece um resumo completo
    print(causal.summary_stats)

    print("\nEstimativas do Efeito Causal:")
    print(causal.estimates)

    # Interpretação do resultado principal: ATT
    att = causal.estimates['matching']['att']
    p_value = causal.estimates['matching']['p-val']

    print("\n--- INTERPRETAÇÃO ---")
    if att < 0:
        print(f"✅ EFEITO PROTETOR ENCONTRADO: A intervenção (pré-natal adequado) CAUSOU uma redução de {abs(att)*100:.2f} pontos percentuais na probabilidade de óbito infantil.")
    else:
        print(f"⚠️ EFEITO NULO OU DE RISCO ENCONTRADO: A intervenção não demonstrou um efeito protetor causal.")

    if p_value < 0.05:
        print(f"O resultado é estatisticamente significante (p-valor = {p_value:.4f}), o que fortalece a conclusão.")
    else:
        print(f"O resultado não é estatisticamente significante (p-valor = {p_value:.4f}), o que enfraquece a conclusão.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa uma análise de impacto causal usando escore de propensão.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        required=True,
        help="Caminho para o painel de dados completo gerado por 'analise_risco_geografico.py'."
    )
    args = parser.parse_args()

    df_completo = carregar_e_preparar_dados(Path(args.input_csv))

    if df_completo is not None and not df_completo.empty:
        analisar_impacto_causal(df_completo)
        print("\n" + "="*80)
        print("🎉 PIPELINE DE ANÁLISE CAUSAL CONCLUÍDO! 🎉")
        print("="*80)
