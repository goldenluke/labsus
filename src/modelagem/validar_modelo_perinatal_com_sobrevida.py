# -*- coding: utf-8 -*-
"""
======================================================================
  VALIDAÇÃO CRUZADA DE MODELOS: AVALIANDO O MODELO DE RISCO PERINATAL
  COM DADOS REAIS DE SOBREVIDA INFANTIL
======================================================================
Este script executa uma validação externa:
1. Carrega o modelo treinado para prever Risco Perinatal (baixo peso/prematuridade).
2. Carrega e prepara um dataset de Sobrevida Infantil, com o desfecho real de óbito.
3. Aplica o modelo de Risco Perinatal ao dataset de Sobrevida para avaliar
   sua capacidade de prever o desfecho "óbito infantil".
"""

import pandas as pd
from pathlib import Path
import argparse
import joblib
import lightgbm as lgb

from sklearn.metrics import roc_auc_score, roc_curve, classification_report
import matplotlib.pyplot as plt

# Reutilizando as funções dos outros scripts
from .modelo_risco_perinatal import preparar_dados as preparar_dados_perinatal
from .analise_sobrevida_infantil import carregar_dados, vincular_obitos_real, enriquecer_com_cnes, preparar_dados_para_modelo as preparar_dados_sobrevida

def validar_modelo_cruzado(dir_modelo_perinatal: Path, ufs: list, ano_coorte: int):
    """
    Orquestra a validação do modelo perinatal com o desfecho de óbito.
    """
    print("="*80)
    print("🚀 INICIANDO VALIDAÇÃO CRUZADA DE MODELOS 🚀")
    print("="*80)

    # --- ETAPA 1: Carregar o modelo de Risco Perinatal treinado ---
    print(f"\n--- [ETAPA 1] Carregando modelo de Risco Perinatal ---")
    caminho_modelo = dir_modelo_perinatal / "modelo_risco_perinatal.joblib"
    try:
        modelo_perinatal = joblib.load(caminho_modelo)
        print(f"✅ Modelo carregado de: {caminho_modelo}")
    except FileNotFoundError:
        print(f"❌ ERRO: Modelo não encontrado em '{caminho_modelo}'.")
        print("   -> Por favor, execute o script 'modelo_risco_perinatal.py' primeiro para treinar o modelo.")
        return

    # --- ETAPA 2: Construir o dataset de teste de Sobrevida Infantil ---
    print("\n--- [ETAPA 2] Construindo dataset de validação com desfecho de óbito ---")

    df_sinasc, df_sim, df_cnes = carregar_dados(ufs=ufs, ano_coorte=ano_coorte)

    if df_sinasc is None or df_sinasc.empty:
        print("❌ Falha ao carregar dados. Abortando validação.")
        return

    df_vinculado = vincular_obitos_real(df_sinasc, df_sim)
    df_enriquecido = enriquecer_com_cnes(df_vinculado, df_cnes)

    # --- CORREÇÃO APLICADA AQUI ---
    # Usa o nome correto da função importada: `preparar_dados_sobrevida`
    X_teste_real, y_teste_real = preparar_dados_sobrevida(df_enriquecido)
    # --- FIM DA CORREÇÃO ---

    if X_teste_real.empty or y_teste_real.nunique() < 2:
        print("❌ Dados de sobrevida insuficientes para realizar a validação.")
        return

    # --- ETAPA 3: Fazer a Previsão e Avaliar ---
    print("\n--- [ETAPA 3] Aplicando o modelo de Risco Perinatal para prever Óbito Infantil ---")

    colunas_do_modelo = modelo_perinatal.feature_name_

    # Verifica se todas as colunas necessárias estão no dataset de teste
    colunas_faltantes = [col for col in colunas_do_modelo if col not in X_teste_real.columns]
    if colunas_faltantes:
        print(f"❌ ERRO: O dataset de sobrevida não contém todas as features esperadas pelo modelo perinatal. Faltam: {colunas_faltantes}")
        return

    X_teste_real_alinhado = X_teste_real[colunas_do_modelo]

    pred_proba_risco_perinatal = modelo_perinatal.predict_proba(X_teste_real_alinhado)[:, 1]

    auc_cruzado = roc_auc_score(y_teste_real, pred_proba_risco_perinatal)

    print("\n" + "="*80)
    print("--- RESULTADO DA VALIDAÇÃO ---")
    print(f"Área sob a Curva ROC (AUC): {auc_cruzado:.4f}")

    if auc_cruzado > 0.75:
        print("\n✅ **CONCLUSÃO:** O modelo treinado para prever Risco Perinatal (baixo peso/prematuridade) demonstrou uma boa capacidade de prever o desfecho final de Óbito Infantil.")
        print("Isso valida o Risco Perinatal como um bom 'proxy' (indicador substituto) para o risco de mortalidade.")
    else:
        print("\n⚠️ **CONCLUSÃO:** O modelo treinado para prever Risco Perinatal não demonstrou uma forte capacidade de prever o desfecho de Óbito Infantil.")
        print("Isso pode indicar que os fatores de risco para baixo peso/prematuridade são diferentes dos fatores que levam ao óbito nesta população.")

    print("="*80)

    # --- ETAPA 4: Visualização ---
    print("\n--- [ETAPA 4] Gerando gráfico da Curva ROC ---")

    fpr, tpr, _ = roc_curve(y_teste_real, pred_proba_risco_perinatal)

    plt.figure(figsize=(8, 8))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Curva ROC (AUC = {auc_cruzado:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0]); plt.ylim([0.0, 1.05])
    plt.xlabel('Taxa de Falsos Positivos'); plt.ylabel('Taxa de Verdadeiros Positivos')
    plt.title('Capacidade do Modelo de Risco Perinatal em Prever Óbito Infantil')
    plt.legend(loc="lower right")

    dir_saida_validacao = Path("outputs/validacao_cruzada")
    dir_saida_validacao.mkdir(parents=True, exist_ok=True)
    caminho_fig = dir_saida_validacao / "roc_validacao_cruzada.png"
    plt.savefig(caminho_fig, dpi=150)
    plt.close()

    print(f"📈 Gráfico da Curva ROC salvo em: {caminho_fig}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Valida o modelo de risco perinatal usando dados de sobrevida infantil."
    )
    parser.add_argument("--dir_modelo", type=str, default="outputs/risco_perinatal",
                        help="Diretório onde o 'modelo_risco_perinatal.joblib' foi salvo.")
    parser.add_argument("--ufs", nargs="+", default=["TO"],
                        help="Lista de UFs para construir o dataset de validação.")
    parser.add_argument("--ano_coorte", type=int, default=2022,
                        help="Ano da coorte de nascimentos para o dataset de validação.")

    args = parser.parse_args()

    validar_modelo_cruzado(
        dir_modelo_perinatal=Path(args.dir_modelo),
        ufs=args.ufs,
        ano_coorte=args.ano_coorte
    )
