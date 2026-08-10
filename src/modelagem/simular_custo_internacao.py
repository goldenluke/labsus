# -*- coding: utf-8 -*-
"""
======================================================================
  SIMULADOR DE CUSTO DE INTERNAÇÃO HOSPITALAR COM IA EXPLICÁVEL (SHAP)
======================================================================
Este script carrega o modelo de regressão treinado e o utiliza para
prever o custo de uma nova internação com base nas características
fornecidas via linha de comando.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import joblib
import shap
import matplotlib.pyplot as plt
import lightgbm as lgb

def prever_custo_individual(dados_internacao: dict, caminho_modelo: Path, caminho_dados_treino: Path):
    """
    Carrega o modelo treinado, prepara os dados da nova internação,
    faz a previsão de custo e gera a interpretação com SHAP.
    """
    print("\n--- 🚀 Iniciando Simulador de Custo de Internação 🚀 ---")

    try:
        modelo = joblib.load(caminho_modelo)
        X_train_data = pd.read_parquet(caminho_dados_treino)
        print(f"[LOG] Modelo e dados de treino carregados com sucesso.")
    except FileNotFoundError as e:
        print(f"❌ ERRO: Arquivo de modelo ou de dados de treino não encontrado. Detalhe: {e}")
        print("      -> Por favor, execute o script 'previsao_custo_internacao.py' primeiro.")
        return

    print("\n[LOG] Preparando os dados da nova internação...")
    df_internacao = pd.DataFrame([dados_internacao])
    df_internacao = df_internacao.reindex(columns=X_train_data.columns)

    for col in X_train_data.columns:
        if str(X_train_data[col].dtype) == 'category':
            df_internacao[col] = pd.Categorical(df_internacao[col], categories=X_train_data[col].cat.categories)
        else:
            df_internacao[col] = df_internacao[col].astype(X_train_data[col].dtype)

    print("\n[LOG] Dados da internação a serem avaliados:")
    print(df_internacao.transpose())

    predicao_log = modelo.predict(df_internacao)[0]
    custo_previsto = np.expm1(predicao_log)

    print("\n" + "="*50)
    print("--- Resultado da Previsão de Custo ---")
    print(f"-> 💰 Custo Estimado para esta Internação: R$ {custo_previsto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    print("="*50)

    # --- CORREÇÃO APLICADA AQUI ---
    print("\n[LOG] Gerando explicação para a previsão com SHAP...")
    # 1. Criamos o explainer sem o fundo de dados para evitar o erro de conversão de tipo.
    explainer = shap.TreeExplainer(modelo)

    # 2. Calculamos o `expected_value` (valor base) manualmente, que é a média das previsões no treino.
    base_value = explainer.expected_value
    if base_value is None: # Algumas versões mais antigas podem não calcular
        base_value = modelo.predict(X_train_data).mean()

    # 3. Calculamos os shap_values para a nossa nova internação.
    shap_values = explainer.shap_values(df_internacao)
    # --- FIM DA CORREÇÃO ---

    feature_name_map = {
        'DIAG_PRINC': 'Diagnóstico Principal (CID-10)','PROC_REA': 'Procedimento Realizado (SIGTAP)','DIAS_PERM': 'Dias de Permanência',
        'IDADE': 'Idade do Paciente','SEXO': 'Sexo','CAR_INT': 'Caráter da Internação','UTI_MES_TO': 'Total de Diárias de UTI',
        'MORTE': 'Desfecho Óbito','TP_UNID': 'Tipo de Unidade Hospitalar','NAT_JUR': 'Natureza Jurídica do Hospital',
        'LEITHOSP': 'Nº Total de Leitos do Hospital','ATIVIDAD': 'Hospital de Ensino/Pesquisa'
    }
    df_internacao_renamed = df_internacao.rename(columns=feature_name_map)

    plt.figure()
    shap.waterfall_plot(shap.Explanation(values=shap_values[0],
                                          base_values=base_value,
                                          data=df_internacao_renamed.iloc[0]),
                        show=False)
    plt.title("Fatores que Influenciam o Custo Previsto (SHAP)")
    plt.tight_layout()
    dir_saida = Path("outputs/simulacoes_custo")
    dir_saida.mkdir(parents=True, exist_ok=True)
    caminho_fig = dir_saida / "explicacao_custo_individual.png"
    plt.savefig(caminho_fig)
    plt.close()
    print(f"📈 Gráfico com a explicação da previsão salvo em: {caminho_fig}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calcula e explica o custo previsto para uma nova internação.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--dias-perm", dest='DIAS_PERM', type=int, required=True, help="Dias de permanência previstos.")
    parser.add_argument("--idade", dest='IDADE', type=int, required=True, help="Idade do paciente.")
    parser.add_argument("--diag-princ", dest='DIAG_PRINC', type=str, required=True, help="CID-10 do diagnóstico principal (ex: I219 para Infarto).")
    parser.add_argument("--proc-rea", dest='PROC_REA', type=str, required=True, help="Código do procedimento principal (SIGTAP).")
    parser.add_argument("--usou-uti", dest='UTI_MES_TO', type=int, default=0, help="Total de dias em UTI.")
    parser.add_argument("--sexo", dest='SEXO', type=str, default='1', help="Sexo do paciente (ex: '1' Masc, '3' Fem).")
    parser.add_argument("--car-int", dest='CAR_INT', type=str, default='02', help="Caráter da internação (ex: '01' Eletivo, '02' Urgência).")
    parser.add_argument("--morte", dest='MORTE', type=int, default=0, choices=[0, 1], help="Se o desfecho esperado é óbito (1=Sim, 0=Não).")
    parser.add_argument("--hosp-leitos", dest='LEITHOSP', type=int, default=150, help="Nº de leitos do hospital.")
    parser.add_argument("--hosp-tipo", dest='TP_UNID', type=str, default='05', help="Tipo de unidade do hospital (ex: '05' Hospital Geral).")
    parser.add_argument("--hosp-natureza", dest='NAT_JUR', type=str, default='2062', help="Natureza jurídica do hospital (ex: '1015' Adm. Pública).")
    parser.add_argument("--hosp-ensino", dest='ATIVIDAD', type=int, default=0, choices=[0,1], help="Se o hospital é de ensino (1=Sim, 0=Não).")
    parser.add_argument("--modelo", type=str, default="outputs/previsao_custo/modelo_custo_internacao.joblib", help="Caminho para o arquivo do modelo treinado (.joblib).")
    args = parser.parse_args()

    dados_internacao = {key: value for key, value in vars(args).items() if key != 'modelo'}

    caminho_modelo_arg = Path(args.modelo)
    caminho_dados_treino_arg = caminho_modelo_arg.parent / "X_train_data.parquet"

    prever_custo_individual(dados_internacao, caminho_modelo_arg, caminho_dados_treino_arg)
