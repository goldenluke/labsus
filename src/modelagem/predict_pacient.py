# -*- coding: utf-8 -*-
"""
Script para Prever o Risco de Readmissão de um Novo Paciente via Linha de Comando.
Versão com engenharia de atributos para corresponder ao novo modelo e sem features de comorbidade.
"""

# --- 1. Importação de Bibliotecas ---
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import shap
import lightgbm as lgb
import matplotlib.pyplot as plt
import argparse

# --- 2. CONFIGURAÇÕES ---
DIR_MODELOS = Path('modelos')
DIR_DADOS_PROCESSADOS = Path('dados_processados')

# --- 3. FUNÇÃO DE ENGENHARIA DE ATRIBUTOS (ESPELHO DO PIPELINE) ---

def engineer_features_for_patient(patient_df):
    """Aplica as mesmas transformações de features do pipeline de treino."""
    print("    -> Aplicando engenharia de atributos...")

    # Criação de features binárias e categóricas
    patient_df['CAPITULO_CID'] = patient_df['DIAG_PRINC'].str[0]

    # Remove a feature original de diagnóstico principal que não é mais usada diretamente
    patient_df = patient_df.drop(columns=['DIAG_PRINC'])

    print("    -> Features transformadas com sucesso.")
    return patient_df


# --- 4. FUNÇÃO DE PREVISÃO ---

def predict_new_patient(patient_data, output_dir):
    """
    Carrega o modelo, prepara os dados de um novo paciente,
    faz a previsão e gera a interpretação.
    """
    print("="*80)
    print("🚀 Iniciando Previsão para Novo Paciente 🚀")
    print("="*80)

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Carregamento do Modelo e do Explainer SHAP ---
    print("1. Carregando o modelo treinado...")
    try:
        model = joblib.load(DIR_MODELOS / 'lgbm_readmission_model.joblib')
        print("    -> Modelo carregado com sucesso.")
    except FileNotFoundError:
        print("ERRO: Arquivo do modelo 'lgbm_readmission_model.joblib' não encontrado.")
        print("Por favor, execute o novo pipeline de treinamento primeiro.")
        return

    print("\n2. Carregando o explainer SHAP (pode levar um momento)...")
    try:
        X_test = pd.read_parquet(DIR_DADOS_PROCESSADOS / 'X_test.parquet')
        explainer = shap.TreeExplainer(model)
        print("    -> Explainer SHAP criado com sucesso.")
    except FileNotFoundError:
        print("ERRO: Arquivo 'X_test.parquet' não encontrado.")
        print("Por favor, execute o novo pipeline de treinamento para gerá-lo.")
        return

    # --- Preparação dos Dados do Novo Paciente ---
    print("\n3. Preparando os dados do novo paciente...")
    patient_df_raw = pd.DataFrame([patient_data])

    # Aplica a mesma engenharia de atributos do pipeline
    patient_df_featured = engineer_features_for_patient(patient_df_raw)

    # Alinha colunas e tipos com o dataset de treino
    patient_df = patient_df_featured.reindex(columns=X_test.columns, fill_value=np.nan)

    for col in X_test.columns:
        if X_test[col].dtype.name == 'category':
            patient_df[col] = pd.Categorical(patient_df[col], categories=X_test[col].cat.categories)
        else:
            patient_df[col] = pd.to_numeric(patient_df[col], errors='coerce')

    print("    -> Dados do paciente para previsão (após transformações):")
    print(patient_df.transpose())


    # --- Realização da Previsão ---
    print("\n4. Realizando a previsão...")
    prediction_proba = model.predict_proba(patient_df)
    risk_score = prediction_proba[0, 1]

    print(f"\n    -> 📈 **Score de Risco de Readmissão em 30 dias: {risk_score:.2%}**")

    # --- Salvar resultado da previsão em CSV ---
    print("\n5. Salvando o resultado da previsão em CSV...")
    resultado_df = patient_df.copy()
    resultado_df['RISCO_READMISSAO_30D'] = risk_score
    output_csv_path = output_dir / 'previsao_paciente_individual.csv'
    resultado_df.to_csv(output_csv_path, sep=';', index=False, encoding='utf-8-sig')
    print(f"    -> Resultado salvo em: {output_csv_path}")


    # --- Interpretação da Previsão com SHAP ---
    print("\n6. Gerando a explicação para esta previsão...")
    shap_values = explainer.shap_values(patient_df)

    if isinstance(shap_values, list): shap_values_risk = shap_values[1]
    else: shap_values_risk = shap_values
    if isinstance(explainer.expected_value, list): base_value = explainer.expected_value[1]
    else: base_value = explainer.expected_value

    feature_name_map = {
        'IDADE': 'Idade', 'DIAS_PERM': 'Dias de Permanência',
        'USOU_UTI': 'Utilizou UTI', 'CAPITULO_CID': 'Grupo do Diagnóstico',
        'SEXO': 'Sexo', 'RACA_COR': 'Raça/Cor', 'CAR_INT': 'Caráter da Internação',
        'HOSP_NATUREZA': 'Natureza do Hospital', 'HOSP_LEITOS': 'Nº de Leitos do Hospital'
    }
    patient_df_renamed = patient_df.rename(columns=feature_name_map)

    # --- Salvar dados do SHAP em CSV ---
    print("\n7. Salvando os dados da explicação SHAP em CSV...")
    explanation_df = pd.DataFrame({
        'feature': patient_df_renamed.columns,
        'feature_value': patient_df_renamed.iloc[0].values,
        'shap_value': shap_values_risk[0]
    })
    base_df = pd.DataFrame([{'feature': 'Valor Base (Risco Médio)', 'feature_value': np.nan, 'shap_value': base_value}])
    final_explanation_df = pd.concat([base_df, explanation_df], ignore_index=True)

    output_shap_csv_path = output_dir / 'shap_explanation_data.csv'
    final_explanation_df.to_csv(output_shap_csv_path, sep=';', index=False, encoding='utf-8-sig')
    print(f"    -> Dados da explicação SHAP salvos em: {output_shap_csv_path}")

    # --- Geração do Gráfico Waterfall ---
    print("\n8. Gerando o gráfico da explicação...")
    fig, ax = plt.subplots(figsize=(12, 8))
    shap.waterfall_plot(
        shap.Explanation(
            values=shap_values_risk[0],
            base_values=base_value,
            data=patient_df_renamed.iloc[0]
        ),
        max_display=15,
        show=False
    )
    plt.tight_layout()
    output_path = output_dir / 'previsao_paciente_individual.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"    -> Gráfico de explicação salvo em: {output_path}")
    print("\n" + "="*80)
    print("🎉 Previsão Concluída! 🎉")
    print("="*80)

# --- 5. BLOCO DE EXECUÇÃO COM ARGPARSE ---
def main():
    """
    Função principal que analisa os argumentos da linha de comando
    e orquestra a previsão.
    """
    parser = argparse.ArgumentParser(
        description="Prevê o risco de readmissão hospitalar para um novo paciente.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--idade", type=int, default=65, help="Idade do paciente em anos.")
    parser.add_argument("--dias_perm", type=int, default=5, help="Total de dias de permanência na internação.")
    parser.add_argument("--usou_uti", type=int, default=0, choices=[0, 1], help="Paciente utilizou UTI? (1 para Sim, 0 para Não).")
    parser.add_argument("--sexo", type=str, default='1', help="Código do sexo do paciente (ex: '1' para Masculino, '3' para Feminino).")

    parser.add_argument("--raca_cor", type=str, default='99', help="Código da Raça/Cor (ex: '1' Branca, '3' Parda). Padrão: 99 (Ignorado).")
    parser.add_argument("--car_int", type=str, default='02', help="Caráter da internação (ex: '01' Eletivo, '02' Urgência). Padrão: 02.")
    parser.add_argument("--diag_princ", type=str, default='I500', help="CID-10 do diagnóstico principal. Padrão: I500.")
    parser.add_argument("--hosp_natureza", type=str, default='3075', help="Código da natureza jurídica do hospital. Padrão: 3075.")
    parser.add_argument("--hosp_leitos", type=int, default=150, help="Número de leitos do hospital. Padrão: 150.")

    parser.add_argument("--dir_saida", type=str, required=True, help="Diretório para salvar os resultados (CSV e imagem).")

    args = parser.parse_args()

    # --- CORREÇÃO: Dicionário atualizado sem N_COMORBIDADES ---
    paciente_a_prever = {
        'IDADE': args.idade,
        'DIAS_PERM': args.dias_perm,
        'USOU_UTI': args.usou_uti,
        'SEXO': args.sexo,
        'RACA_COR': args.raca_cor,
        'CAR_INT': args.car_int,
        'DIAG_PRINC': args.diag_princ,
        'HOSP_NATUREZA': args.hosp_natureza,
        'HOSP_LEITOS': args.hosp_leitos
    }

    output_directory = Path(args.dir_saida)

    predict_new_patient(paciente_a_prever, output_directory)

if __name__ == "__main__":
    main()
