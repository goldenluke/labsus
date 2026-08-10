# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE EXPLORATÓRIA VISUAL DOS FATORES DE RISCO PERINATAL
======================================================================
Este script carrega os dados do SINASC e gera gráficos intuitivos para
visualizar a relação entre os principais fatores de risco e a ocorrência
de nascimentos de baixo peso ou prematuridade.

Utiliza rótulos amigáveis para facilitar a interpretação.
"""

import pandas as pd
from pathlib import Path
import argparse
import matplotlib.pyplot as plt
import seaborn as sns

# Para reutilizar as funções de carregamento e preparação de dados.
try:
    from src.modelagem.modelo_risco_perinatal import carregar_dados_sinasc, preparar_dados
except ImportError:
    print("ERRO: Não foi possível importar 'src.modelagem.modelo_risco_perinatal'.")
    print("Execute este script a partir da raiz do projeto (ex: python -m src.modelagem.analise_exploratoria_risco).")
    exit()

# Dicionários para Rótulos Amigáveis (baseado no SINASC.md)
mapa_escolaridade = {
    0: 'Sem Escolaridade',
    1: 'Fundamental I (1-4)',
    2: 'Fundamental II (5-8)',
    3: 'Ensino Médio',
    4: 'Superior Incompleto',
    5: 'Superior Completo',
    9: 'Ignorado'
}

def plotar_risco_por_consultas(df_risco: pd.DataFrame, dir_saida: Path):
    """Gera um gráfico da % de risco por número de consultas de pré-natal."""
    print("  -> Gerando gráfico: Risco por Consultas de Pré-Natal...")

    # Agrupa os dados e calcula a média do risco (que é a %)
    dados_plot = df_risco.groupby('CONSPRENAT')['ALVO_RISCO'].mean().reset_index()
    dados_plot['ALVO_RISCO'] *= 100 # Converte para percentual

    plt.figure(figsize=(12, 7))
    sns.barplot(x='CONSPRENAT', y='ALVO_RISCO', data=dados_plot, palette='coolwarm')

    plt.title('Risco de Baixo Peso ou Prematuridade vs. Consultas de Pré-Natal', fontsize=16)
    plt.xlabel('Número de Consultas de Pré-Natal', fontsize=12)
    plt.ylabel('Percentual de Nascimentos de Risco (%)', fontsize=12)
    plt.ylim(0, max(dados_plot['ALVO_RISCO']) * 1.1) # Ajusta o limite do eixo y

    caminho_fig = dir_saida / "grafico_risco_por_consultas.png"
    plt.savefig(caminho_fig)
    plt.close()
    print(f"     -> Gráfico salvo em: {caminho_fig}")

def plotar_risco_por_idade_mae(df_risco: pd.DataFrame, dir_saida: Path):
    """Gera um gráfico da % de risco por faixa etária da mãe."""
    print("  -> Gerando gráfico: Risco por Faixa Etária da Mãe...")

    # Cria faixas etárias
    bins = [0, 19, 34, 100]
    labels = ['Menos de 20 anos', '20 a 34 anos', '35 anos ou mais']
    df_risco['FAIXA_ETARIA'] = pd.cut(df_risco['IDADEMAE'], bins=bins, labels=labels, right=True)

    dados_plot = df_risco.groupby('FAIXA_ETARIA')['ALVO_RISCO'].mean().reset_index()
    dados_plot['ALVO_RISCO'] *= 100

    plt.figure(figsize=(10, 6))
    sns.barplot(x='FAIXA_ETARIA', y='ALVO_RISCO', data=dados_plot, palette='plasma')

    plt.title('Risco de Baixo Peso ou Prematuridade por Faixa Etária da Mãe', fontsize=16)
    plt.xlabel('Faixa Etária da Mãe', fontsize=12)
    plt.ylabel('Percentual de Nascimentos de Risco (%)', fontsize=12)

    caminho_fig = dir_saida / "grafico_risco_por_idade.png"
    plt.savefig(caminho_fig)
    plt.close()
    print(f"     -> Gráfico salvo em: {caminho_fig}")

def plotar_risco_por_escolaridade(df_risco: pd.DataFrame, dir_saida: Path):
    """Gera um gráfico da % de risco por escolaridade da mãe."""
    print("  -> Gerando gráfico: Risco por Escolaridade da Mãe...")

    # Aplica os rótulos amigáveis
    df_risco['ESCOLARIDADE_MAE'] = df_risco['ESCMAE2010'].map(mapa_escolaridade).fillna('Ignorado')

    # Ordena as categorias de escolaridade
    ordem_escolaridade = [
        'Sem Escolaridade', 'Fundamental I (1-4)', 'Fundamental II (5-8)',
        'Ensino Médio', 'Superior Incompleto', 'Superior Completo', 'Ignorado'
    ]

    dados_plot = df_risco.groupby('ESCOLARIDADE_MAE')['ALVO_RISCO'].mean().reindex(ordem_escolaridade).reset_index()
    dados_plot['ALVO_RISCO'] *= 100

    plt.figure(figsize=(14, 8))
    sns.barplot(x='ESCOLARIDADE_MAE', y='ALVO_RISCO', data=dados_plot, palette='viridis')

    plt.title('Risco de Baixo Peso ou Prematuridade por Escolaridade da Mãe', fontsize=16)
    plt.xlabel('Escolaridade da Mãe', fontsize=12)
    plt.ylabel('Percentual de Nascimentos de Risco (%)', fontsize=12)
    plt.xticks(rotation=25, ha='right')
    plt.tight_layout()

    caminho_fig = dir_saida / "grafico_risco_por_escolaridade.png"
    plt.savefig(caminho_fig)
    plt.close()
    print(f"     -> Gráfico salvo em: {caminho_fig}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera gráficos exploratórios sobre os fatores de risco perinatal.")

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar. Ex: TO SP RJ")
    parser.add_argument("--anos", nargs="+", type=int, default=[2023], help="Anos de dados históricos a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_perinatal_exploratoria", help="Diretório para salvar os gráficos.")

    args = parser.parse_args()

    output_dir = Path(args.dir_saida)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Carrega e prepara os dados usando as funções do script de modelagem
    df_raw = carregar_dados_sinasc(ufs=args.ufs, anos=args.anos)

    if not df_raw.empty:
        X, y = preparar_dados(df_raw)

        if not X.empty:
            # Junta as features (X) com o alvo (y) para a análise exploratória
            df_analise = X.join(y)

            print("\n--- [ETAPA EXTRA] Gerando Gráficos Exploratórios ---")
            plotar_risco_por_consultas(df_analise, output_dir)
            plotar_risco_por_idade_mae(df_analise, output_dir)
            plotar_risco_por_escolaridade(df_analise, output_dir)

            print("\n" + "="*80)
            print("🎉 ANÁLISE EXPLORATÓRIA CONCLUÍDA COM SUCESSO! 🎉")
            print(f"Verifique os gráficos em: {output_dir}")
            print("="*80)
