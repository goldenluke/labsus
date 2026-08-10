# -*- coding: utf-8 -*-
"""
======================================================================
  APLICAÇÃO DO MODELO DE RISCO DE ÓBITO INFANTIL COM SHAP
======================================================================
Este script carrega o modelo de sobrevida infantil treinado e o aplica
para prever o risco de óbito para um novo recém-nascido, com base em
suas características clínicas e do hospital de nascimento.
"""

import pandas as pd
from pathlib import Path
import argparse
import joblib
import shap
import matplotlib.pyplot as plt

# Reutilizando a função de preparação de dados do script de treino
try:
    from src.modelagem.analise_sobrevida_infantil import preparar_dados_para_modelo
except ImportError:
    print("ERRO: Certifique-se de que este script está na mesma pasta que 'analise_sobrevida_infantil.py'")
    preparar_dados_para_modelo = None


def prever_risco_obito(dados_nascimento: dict, caminho_modelo: Path, caminho_dados_treino: Path):
    """
    Carrega o modelo, prepara os dados do recém-nascido e retorna a previsão de risco,
    juntamente com uma análise SHAP.
    """
    print("\n--- 🚀 Aplicando Modelo de Risco de Óbito Infantil com SHAP 🚀 ---")

    try:
        modelo = joblib.load(caminho_modelo)
        print(f"[LOG] Modelo '{caminho_modelo.name}' carregado com sucesso.")
    except FileNotFoundError:
        print(f"❌ ERRO: Modelo não encontrado em '{caminho_modelo}'."); return

    colunas_do_modelo = [
        'PESO', 'GESTACAO', 'APGAR5', 'IDADEMAE', 'ESCMAE2010', 'CONSPRENAT',
        'QTDFILVIVO', 'QTDFILMORT', 'PARTO', 'RACACORMAE',
        'QTLEIT39', 'ATIVIDAD'
    ]
    df_nascimento = pd.DataFrame([dados_nascimento], columns=colunas_do_modelo)

    print("\n[LOG] Dados do recém-nascido a serem avaliados:")
    print(df_nascimento.transpose())

    probabilidade_risco = modelo.predict_proba(df_nascimento)[0, 1]

    print("\n" + "="*60)
    print("--- Resultado da Previsão de Risco de Sobrevida ---")
    print(f"-> 🚨 Probabilidade de Risco de Óbito Infantil: {probabilidade_risco:.2%}")

    if probabilidade_risco > 0.10:
        print("-> AVALIAÇÃO: RISCO ELEVADO. Recomenda-se atenção máxima.")
    elif probabilidade_risco > 0.05:
        print("-> AVALIAÇÃO: RISCO MODERADO. Recomenda-se monitoramento intensivo.")
    else:
        print("-> AVALIAÇÃO: RISCO BAIXO. Manter cuidados padrão.")
    print("="*60)

    print("\n[LOG] Gerando explicação para a previsão com SHAP...")

    if preparar_dados_para_modelo is None or not caminho_dados_treino.exists():
        print("⚠️ Aviso: Arquivo de dados de treino não encontrado. Não é possível gerar o gráfico SHAP."); return

    df_treino_completo = pd.read_csv(caminho_dados_treino, sep=';')
    X_treino, _ = preparar_dados_para_modelo(df_treino_completo)

    background_data = shap.sample(X_treino, 100) if len(X_treino) > 100 else X_treino

    explainer = shap.TreeExplainer(modelo, background_data)
    shap_explanation = explainer(df_nascimento)

    mapa_rotulos = {
        'PESO': 'Peso ao Nascer (g)', 'GESTACAO': 'Semanas de Gestação', 'APGAR5': 'Apgar (5º Min)',
        'IDADEMAE': 'Idade da Mãe', 'ESCMAE2010': 'Escolaridade da Mãe', 'CONSPRENAT': 'Nº Consultas Pré-Natal',
        'QTDFILVIVO': 'Nº de Filhos Vivos', 'QTDFILMORT': 'Nº de Filhos Mortos', 'PARTO': 'Tipo de Parto',
        'RACACORMAE': 'Raça/Cor da Mãe', 'QTLEIT39': 'Leitos UTI Neonatal', 'ATIVIDAD': 'Hospital de Ensino'
    }

    # Seleciona a explicação para a primeira (e única) amostra
    explicacao_amostra_unica = shap_explanation[0]

    # Atribui os nomes amigáveis a esta explicação específica
    explicacao_amostra_unica.feature_names = [mapa_rotulos.get(f, f) for f in df_nascimento.columns]

    # ==========================================================
    # --- CORREÇÃO APLICADA AQUI ---
    # Para o waterfall plot de um classificador binário, passamos a explicação
    # da amostra inteira. Por padrão, ele irá plotar a explicação para a classe 1 (risco).
    plt.figure()
    shap.waterfall_plot(explicacao_amostra_unica, show=False)
    # ==========================================================

    plt.title("Fatores que Contribuem para o Risco de Óbito", fontsize=14)
    plt.tight_layout()

    dir_saida = Path("outputs/previsoes_individuais")
    dir_saida.mkdir(parents=True, exist_ok=True)
    caminho_fig = dir_saida / "explicacao_risco_obito_individual.png"
    plt.savefig(caminho_fig, dpi=150)
    plt.close()
    print(f"📈 Gráfico com a explicação da previsão salvo em: {caminho_fig}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calcula e explica o risco de óbito para um novo recém-nascido.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--peso", type=int, required=True, help="Peso ao nascer em gramas (ex: 2200).")
    parser.add_argument("--gestacao", type=int, required=True, help="Semanas de gestação em faixa (ex: 4 para 32-36 semanas).")
    parser.add_argument("--apgar5", type=int, required=True, help="Índice de Apgar no 5º minuto (0 a 10).")
    parser.add_argument("--idade-mae", type=int, required=True, help="Idade da mãe em anos.")
    parser.add_argument("--consultas-prenatal", type=int, required=True, help="Número total de consultas de pré-natal.")
    parser.add_argument("--filhos-vivos", type=int, default=0, help="Nº de filhos vivos anteriores.")
    parser.add_argument("--filhos-mortos", type=int, default=0, help="Nº de filhos mortos anteriores.")
    parser.add_argument("--escolaridade", type=int, default=9, help="Código de escolaridade da mãe (0-5).")
    parser.add_argument("--parto", type=int, default=1, help="Tipo de parto (1: Vaginal, 2: Cesáreo).")
    parser.add_argument("--raca-cor", type=int, default=9, help="Código da raça/cor da mãe (1-5).")

    parser.add_argument("--leitos-uti-neo", type=int, required=True, help="Número de leitos de UTI Neonatal no hospital.")
    parser.add_argument("--hosp-ensino", type=int, default=0, choices=[0,1], help="Se o hospital é de ensino (1=Sim, 0=Não).")

    parser.add_argument("--modelo", type=str, default="outputs/analise_sobrevida/modelo_sobrevida_infantil.joblib", help="Caminho para o modelo treinado.")
    parser.add_argument("--dados-treino-csv", type=str, required=True, help="Caminho para o CSV usado no treino ('painel_sobrevida_infantil_*.csv'), necessário para o fundo do SHAP.")

    args = parser.parse_args()

    dados_rn = {
        'PESO': args.peso, 'GESTACAO': args.gestacao, 'APGAR5': args.apgar5,
        'IDADEMAE': args.idade_mae, 'ESCMAE2010': args.escolaridade,
        'CONSPRENAT': args.consultas_prenatal, 'QTDFILVIVO': args.filhos_vivos,
        'QTDFILMORT': args.filhos_mortos, 'PARTO': args.parto,
        'RACACORMAE': args.raca_cor, 'QTLEIT39': args.leitos_uti_neo,
        'ATIVIDAD': args.hosp_ensino
    }

    prever_risco_obito(dados_rn, Path(args.modelo), Path(args.dados_treino_csv))
