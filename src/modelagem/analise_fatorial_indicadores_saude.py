# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE FATORIAL EXPLORATÓRIA DO PAINEL DE INDICADORES DE SAÚDE
======================================================================
Quando se tem dezenas de indicadores municipais simultâneos, muitos deles
estão correlacionados entre si porque refletem a MESMA dimensão latente
subjacente (ex.: vários indicadores de acesso à atenção primária tendem a
se mover juntos). Este script aplica Análise Fatorial Exploratória para
reduzir o painel de indicadores a um pequeno número de FATORES LATENTES
interpretáveis (ex.: um fator "Vulnerabilidade Materno-Infantil", outro
"Cobertura de Atenção Primária") — diferente de uma simples redução por
PCA (que maximiza variância explicada sem se importar com
interpretabilidade), a Análise Fatorial com rotação Varimax busca
explicitamente fatores mais fáceis de NOMEAR e EXPLICAR para gestores.

Cada município recebe um "escore fatorial" em cada dimensão latente,
utilizável como um índice sintético para ranqueamento/priorização.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import FactorAnalysis
from sklearn.preprocessing import StandardScaler


def carregar_painel(caminho_csv: Path, ufs: list, ano: int, indicadores: list = None):
    df = pd.read_csv(caminho_csv, sep=';', dtype={'cod_mun_ibge_6': str})
    if ufs:
        df = df[df['UF'].isin(ufs)]
    if ano:
        df = df[df['ANO'] == ano]

    if indicadores:
        colunas_indicadores = [c for c in indicadores if c in df.columns]
    else:
        numericas = df.select_dtypes(include=np.number).columns.tolist()
        colunas_indicadores = [c for c in numericas if c.isupper() and c not in ('ANO',)]

    df_final = df[['cod_mun_ibge_6', 'UF', 'municipio'] + colunas_indicadores].dropna()
    return df_final, colunas_indicadores


def calcular_autovalores(X_scaled: np.ndarray) -> np.ndarray:
    """Autovalores da matriz de correlação — usados para o Critério de Kaiser
    (nº de fatores sugerido = nº de autovalores > 1)."""
    matriz_correlacao = np.corrcoef(X_scaled, rowvar=False)
    autovalores = np.linalg.eigvalsh(matriz_correlacao)[::-1]
    return autovalores


def ajustar_analise_fatorial(X_scaled: np.ndarray, n_fatores: int):
    fa = FactorAnalysis(n_components=n_fatores, rotation='varimax', random_state=42)
    escores = fa.fit_transform(X_scaled)
    return fa, escores


def nomear_fatores(cargas: pd.DataFrame, top_n: int = 4) -> dict:
    nomes = {}
    for fator in cargas.columns:
        top_indicadores = cargas[fator].abs().sort_values(ascending=False).head(top_n).index.tolist()
        nomes[fator] = " + ".join(top_indicadores)
    return nomes


def gerar_grafico_scree(autovalores: np.ndarray, dir_saida: Path):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(9, 6))
    plt.plot(range(1, len(autovalores) + 1), autovalores, marker='o')
    plt.axhline(1, color='red', linestyle='--', label='Critério de Kaiser (autovalor = 1)')
    plt.xlabel('Fator')
    plt.ylabel('Autovalor')
    plt.title('Gráfico de Sedimentação (Scree Plot) — Nº de Fatores Sugerido')
    plt.legend()
    caminho_fig = dir_saida / "scree_plot_analise_fatorial.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Scree plot salvo em: {caminho_fig}")


def gerar_heatmap_cargas(cargas: pd.DataFrame, dir_saida: Path):
    import matplotlib.pyplot as plt
    import seaborn as sns

    plt.figure(figsize=(max(8, len(cargas.columns) * 1.5), max(6, len(cargas) * 0.4)))
    sns.heatmap(cargas, annot=True, fmt='.2f', cmap='RdBu_r', center=0, vmin=-1, vmax=1)
    plt.title('Cargas Fatoriais (rotação Varimax)')
    plt.tight_layout()
    caminho_fig = dir_saida / "cargas_fatoriais_heatmap.png"
    plt.savefig(caminho_fig, dpi=150)
    plt.close()
    print(f"📈 Heatmap de cargas fatoriais salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando painel de indicadores ---")
    df, colunas_indicadores = carregar_painel(Path(args.painel_csv), args.ufs, args.ano, args.indicadores)
    print(f"✅ {len(df)} municípios, {len(colunas_indicadores)} indicadores: {colunas_indicadores}")

    if len(df) < len(colunas_indicadores) * 3:
        print(f"⚠️ Aviso: apenas {len(df)} municípios para {len(colunas_indicadores)} indicadores — recomenda-se ao menos 3x mais observações do que variáveis para uma Análise Fatorial estável.")

    X_scaled = StandardScaler().fit_transform(df[colunas_indicadores].values)

    print(f"\n--- [ETAPA 2] Calculando autovalores (Critério de Kaiser) ---")
    autovalores = calcular_autovalores(X_scaled)
    n_fatores_sugerido = int((autovalores > 1).sum()) or 1
    print(f"Autovalores: {np.round(autovalores, 2).tolist()}")
    print(f"✅ Número de fatores sugerido pelo Critério de Kaiser: {n_fatores_sugerido}")
    gerar_grafico_scree(autovalores, dir_saida)

    n_fatores = args.n_fatores or n_fatores_sugerido
    print(f"\n--- [ETAPA 3] Ajustando Análise Fatorial com {n_fatores} fatores (rotação Varimax) ---")
    fa, escores = ajustar_analise_fatorial(X_scaled, n_fatores)

    nomes_fatores = [f'FATOR_{i + 1}' for i in range(n_fatores)]
    cargas = pd.DataFrame(fa.components_.T, index=colunas_indicadores, columns=nomes_fatores)
    nomes_interpretativos = nomear_fatores(cargas)

    print("\n" + "=" * 80)
    print("--- RESULTADO: FATORES LATENTES IDENTIFICADOS ---")
    print("=" * 80)
    for fator, nome in nomes_interpretativos.items():
        print(f"\n{fator} (dominado por: {nome})")
        top_cargas = cargas[fator].sort_values(key=abs, ascending=False).head(6)
        print(top_cargas.round(3).to_string())
    print("=" * 80)

    caminho_cargas = dir_saida / "cargas_fatoriais.csv"
    cargas.to_csv(caminho_cargas, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Cargas fatoriais salvas em: '{caminho_cargas}'")
    gerar_heatmap_cargas(cargas, dir_saida)

    df_escores = df[['cod_mun_ibge_6', 'UF', 'municipio']].copy()
    for i, nome in enumerate(nomes_fatores):
        df_escores[nome] = escores[:, i]
    caminho_escores = dir_saida / "escores_fatoriais_municipios.csv"
    df_escores.to_csv(caminho_escores, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Escores fatoriais por município salvos em: '{caminho_escores}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE FATORIAL EXPLORATÓRIA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reduz o painel de indicadores de saúde a fatores latentes interpretáveis (Análise Fatorial Exploratória).")
    parser.add_argument("--painel-csv", type=str, required=True, help="Caminho para o painel de indicadores (gerado por integrar_indicadores.py).")
    parser.add_argument("--ufs", nargs="+", default=None, help="Lista de UFs a incluir (opcional).")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--indicadores", nargs="+", default=None, help="Lista de indicadores a usar (opcional; detecta automaticamente se omitido).")
    parser.add_argument("--n-fatores", type=int, default=None, help="Número de fatores a extrair (opcional; se omitido, usa o Critério de Kaiser).")
    parser.add_argument("--dir_saida", type=str, default="outputs/analise_fatorial_indicadores", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
