# -*- coding: utf-8 -*-
"""
======================================================================
  SIMULADOR DE IMPACTO DE POLÍTICAS PÚBLICAS
======================================================================
Este script utiliza um modelo de Machine Learning treinado para simular
o impacto potencial de intervenções de saúde pública sobre desfechos
de interesse.

Caso de Uso: Simular o impacto do aumento da cobertura de pré-natal
adequado na redução de nascimentos de alto risco (baixo peso/prematuridade).
"""

import pandas as pd
from pathlib import Path
import argparse
import joblib

# Reutilizando a função de preparação de dados do modelo de risco
try:
    from src.modelagem.modelo_risco_perinatal import preparar_dados
except ImportError:
    print("ERRO: Certifique-se de que este script está na mesma pasta que 'modelo_risco_perinatal.py'")
    preparar_dados = None


def carregar_artefatos(caminho_modelo: Path, caminho_painel_base: Path):
    """Carrega o modelo treinado e o painel de dados da população."""
    print("\n--- [ETAPA 1] Carregando modelo e dados de linha de base ---")

    try:
        modelo = joblib.load(caminho_modelo)
        print(f"✅ Modelo '{caminho_modelo.name}' carregado com sucesso.")
    except FileNotFoundError:
        print(f"❌ ERRO: Modelo não encontrado em '{caminho_modelo}'.")
        return None, None

    try:
        df_base = pd.read_csv(caminho_painel_base, sep=';')
        print(f"✅ Painel de dados base carregado de '{caminho_painel_base.name}' com {len(df_base)} registros.")
    except FileNotFoundError:
        print(f"❌ ERRO: Painel de dados não encontrado em '{caminho_painel_base}'.")
        return None, None

    return modelo, df_base


def executar_simulacao(modelo, df_base: pd.DataFrame, limiar_risco: float):
    """
    Executa a simulação, comparando o cenário real com o cenário de intervenção.
    """
    print("\n--- [ETAPA 2] Executando a simulação de impacto ---")

    # 1. Preparar o dataset para o modelo
    if preparar_dados is None: return
    X_base, _ = preparar_dados(df_base)

    if X_base.empty:
        print("❌ Nenhum dado válido para simulação após a preparação.")
        return

    # 2. Cenário Real (Linha de Base)
    print("[LOG] Calculando risco para o cenário real (linha de base)...")
    pred_proba_base = modelo.predict_proba(X_base)[:, 1]
    casos_risco_base = (pred_proba_base > limiar_risco).sum()

    # 3. Cenário de Intervenção
    print("[LOG] Criando o cenário contrafactual da intervenção...")
    # Intervenção: Garantir que todas as gestantes com menos de 7 consultas
    # (código < 4) passem a ter 7 ou mais consultas (código 4).

    X_intervencao = X_base.copy()
    populacao_alvo_mask = X_intervencao['CONSPRENAT'] < 4

    X_intervencao.loc[populacao_alvo_mask, 'CONSPRENAT'] = 4

    print(f"  -> {populacao_alvo_mask.sum()} gestantes foram incluídas na intervenção simulada.")

    print("[LOG] Calculando risco para o cenário com intervenção...")
    pred_proba_intervencao = modelo.predict_proba(X_intervencao)[:, 1]
    casos_risco_intervencao = (pred_proba_intervencao > limiar_risco).sum()

    # 4. Calcular e apresentar os resultados
    casos_evitados = casos_risco_base - casos_risco_intervencao
    reducao_percentual = (casos_evitados / casos_risco_base) * 100 if casos_risco_base > 0 else 0

    print("\n" + "="*80)
    print("--- RESULTADOS DA SIMULAÇÃO DE IMPACTO DA POLÍTICA PÚBLICA ---")
    print("Intervenção Simulada: Garantir pré-natal adequado (7+ consultas) para todas as gestantes.")
    print("="*80)
    print(f"Total de Nascimentos na Coorte: {len(X_base)}")
    print("-" * 40)
    print(f"Cenário Real (Linha de Base):")
    print(f"  -> Número de Nascimentos de Alto Risco Previstos: {casos_risco_base}")
    print("-" * 40)
    print(f"Cenário com Intervenção (Contrafactual):")
    print(f"  -> Número de Nascimentos de Alto Risco Previstos: {casos_risco_intervencao}")
    print("-" * 40)
    print("\n--- IMPACTO ESTIMADO DA INTERVENÇÃO ---")
    print(f"✅ Casos de Alto Risco Evitados: {casos_evitados}")
    print(f"✅ Redução Percentual no Risco: {reducao_percentual:.2f}%")
    print("="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simula o impacto de uma política de saúde usando um modelo preditivo treinado.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--painel-base-csv",
        type=str,
        required=True,
        help="Caminho para o painel de dados de nascimentos a ser usado como linha de base (gerado por 'analise_sobrevida_infantil.py')."
    )
    parser.add_argument(
        "--modelo-risco",
        type=str,
        default="outputs/risco_perinatal/modelo_risco_perinatal.joblib",
        help="Caminho para o modelo de risco perinatal treinado."
    )
    parser.add_argument(
        "--limiar-risco",
        type=float,
        default=0.5,
        help="Limiar de probabilidade para classificar um nascimento como 'Alto Risco'."
    )

    args = parser.parse_args()

    # Pipeline
    modelo_carregado, df_base_raw = carregar_artefatos(Path(args.modelo_risco), Path(args.painel_base_csv))

    if modelo_carregado is not None and df_base_raw is not None:
        executar_simulacao(modelo_carregado, df_base_raw, args.limiar_risco)
