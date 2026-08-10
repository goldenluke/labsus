# -*- coding: utf-8 -*-
"""
Script para Prever o Risco Perinatal de uma Nova Gestante.

Este script carrega o modelo treinado e o utiliza para prever o risco
de baixo peso/prematuridade para uma gestante cujas características
são fornecidas como argumentos de linha de comando.

Exemplo de Uso no Terminal:
python predict_risco_perinatal.py --idade 17 --consultas 3 --mes_prenatal 5 --filhos_vivos 0
"""

# --- 1. Importação de Bibliotecas ---
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import shap
import lightgbm as lgb # Necessário para o joblib carregar o modelo
import matplotlib.pyplot as plt
import argparse

# --- 2. CONFIGURAÇÕES ---
DIR_MODELOS = Path('outputs/risco_perinatal')
DIR_OUTPUTS = Path('outputs/risco_perinatal')
DIR_OUTPUTS.mkdir(exist_ok=True)

# --- 3. FUNÇÃO PRINCIPAL DE PREVISÃO ---

def predict_new_gestante(gestante_data, X_train_columns):
    """
    Carrega o modelo, prepara os dados de uma nova gestante,
    faz a previsão e gera a interpretação.
    """
    print("="*80)
    print("🚀 Iniciando Previsão de Risco Perinatal 🚀")
    print("="*80)

    # --- Carregamento do Modelo e do Explainer SHAP ---
    print("1. Carregando o modelo treinado...")
    model_path = DIR_MODELOS / "modelo_risco_perinatal.joblib"
    try:
        model = joblib.load(model_path)
        print("   -> Modelo carregado com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo do modelo '{model_path}' não encontrado.")
        print("Por favor, execute o pipeline de treinamento primeiro.")
        return

    print("\n2. Criando o explainer SHAP...")
    explainer = shap.TreeExplainer(model)
    print("   -> Explainer SHAP criado com sucesso.")

    # --- Preparação dos Dados da Nova Gestante ---
    print("\n3. Preparando os dados da nova gestante...")

    # Converte o dicionário de dados para um DataFrame
    gestante_df = pd.DataFrame([gestante_data])

    # Garante que o DataFrame tenha exatamente as mesmas colunas e na mesma ordem
    gestante_df = gestante_df.reindex(columns=X_train_columns, fill_value=np.nan)

    print("   -> Dados da gestante para previsão:")
    print(gestante_df.transpose())

    # --- Realização da Previsão ---
    print("\n4. Realizando a previsão...")
    prediction_proba = model.predict_proba(gestante_df)
    risk_score = prediction_proba[0, 1]  # Probabilidade da classe 1 (Risco)

    print(f"\n   -> 📈 **Probabilidade de Risco Perinatal (Baixo Peso ou Prematuridade): {risk_score:.2%}**")

    # --- Interpretação da Previsão com SHAP ---
    print("\n5. Gerando a explicação para esta previsão...")
    shap_values = explainer.shap_values(gestante_df)

    if isinstance(shap_values, list): shap_values_risk = shap_values[1]
    else: shap_values_risk = shap_values
    if isinstance(explainer.expected_value, list): base_value = explainer.expected_value[1]
    else: base_value = explainer.expected_value

    mapa_rotulos = {
        'IDADEMAE': 'Idade da Mãe', 'ESCMAE2010': 'Escolaridade da Mãe', 'RACACORMAE': 'Raça/Cor da Mãe',
        'QTDFILVIVO': 'Nº de Filhos Vivos', 'QTDFILMORT': 'Nº de Filhos Mortos', 'CONSPRENAT': 'Nº Consultas Pré-Natal',
        'MESPRENAT': 'Mês Início Pré-Natal', 'PARTO': 'Tipo de Parto', 'GRAVIDEZ': 'Tipo de Gravidez',
        'ESTCIVMAE': 'Estado Civil da Mãe'
    }
    gestante_df_renamed = gestante_df.rename(columns=mapa_rotulos)

    fig, ax = plt.subplots(figsize=(12, 8))
    shap.waterfall_plot(
        shap.Explanation(
            values=shap_values_risk[0],
            base_values=base_value,
            data=gestante_df_renamed.iloc[0]
        ),
        max_display=15,
        show=False
    )
    plt.tight_layout()
    output_path = DIR_OUTPUTS / 'previsao_gestante_individual.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"   -> Gráfico de explicação salvo em: {output_path}")
    print("\n" + "="*80)
    print("🎉 Previsão Concluída! 🎉")
    print("="*80)

# --- 4. BLOCO DE EXECUÇÃO COM ARGPARSE ---
def main():
    """
    Função principal que analisa os argumentos da linha de comando
    e orquestra a previsão.
    """
    # Colunas que o modelo espera, na ordem correta
    # Esta lista deve ser idêntica à de `X` no script de treinamento
    expected_columns = [
        'IDADEMAE', 'ESCMAE2010', 'RACACORMAE', 'QTDFILVIVO',
        'QTDFILMORT', 'CONSPRENAT', 'MESPRENAT', 'PARTO',
        'GRAVIDEZ', 'ESTCIVMAE'
    ]

    parser = argparse.ArgumentParser(
        description="Prevê o risco perinatal para uma nova gestante.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Argumentos para as features do modelo
    parser.add_argument("--idade", type=int, required=True, dest='IDADEMAE', help="Idade da mãe em anos.")
    parser.add_argument("--consultas", type=int, required=True, dest='CONSPRENAT', help="Número total de consultas de pré-natal.")
    parser.add_argument("--mes_prenatal", type=int, required=True, dest='MESPRENAT', help="Mês de gestação em que o pré-natal iniciou.")
    parser.add_argument("--filhos_vivos", type=int, required=True, dest='QTDFILVIVO', help="Número de filhos vivos anteriores.")

    # Argumentos opcionais com valores padrão
    parser.add_argument("--escolaridade", type=int, default=3, dest='ESCMAE2010', help="Escolaridade da mãe (0-5, Padrão: 3-Ensino Médio).")
    parser.add_argument("--raca", type=int, default=4, dest='RACACORMAE', help="Raça/Cor da mãe (1-Branca, 2-Preta, 3-Amarela, 4-Parda, 5-Indígena. Padrão: 4).")
    parser.add_argument("--filhos_mortos", type=int, default=0, dest='QTDFILMORT', help="Número de filhos mortos anteriores (abortos/natimortos). Padrão: 0.")
    parser.add_argument("--parto", type=int, default=1, dest='PARTO', help="Tipo de parto esperado/anterior (1-Vaginal, 2-Cesáreo). Padrão: 1.")
    parser.add_argument("--gravidez", type=int, default=1, dest='GRAVIDEZ', help="Tipo de gravidez (1-Única, 2-Dupla, 3-Tripla+). Padrão: 1.")
    parser.add_argument("--est_civil", type=int, default=5, dest='ESTCIVMAE', help="Estado civil da mãe (1-Solteira, 2-Casada, 5-União Estável, etc). Padrão: 5.")

    args = parser.parse_args()

    # Constrói o dicionário do paciente a partir dos argumentos
    # `vars(args)` converte o objeto de argumentos em um dicionário
    gestante_a_prever = vars(args)

    # Chama a função de previsão
    predict_new_gestante(gestante_a_prever, expected_columns)

if __name__ == "__main__":
    main()
