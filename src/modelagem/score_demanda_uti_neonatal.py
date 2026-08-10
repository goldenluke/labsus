# -*- coding: utf-8 -*-
"""
======================================================================
  SCORE DE PRIORIZAÇÃO PARA ALOCAÇÃO DE LEITOS DE UTI NEONATAL
======================================================================
Este script cruza DEMANDA PROJETADA (nº esperado de nascimentos de alto
risco — baixo peso/prematuridade — por município, estimado aplicando o
modelo treinado em `modelo_risco_perinatal.py` a cada nascimento real do
período) com OFERTA ATUAL (nº de leitos de UTI Neonatal cadastrados no
CNES, campo QTLEIT39, por município) para calcular um ÍNDICE DE
PRIORIZAÇÃO: municípios com muita demanda esperada e pouca (ou nenhuma)
oferta de leito de UTI neonatal aparecem no topo do ranking — a pergunta
direta de planejamento "onde investir em novos leitos primeiro?".
"""

import argparse
from pathlib import Path

import joblib
import pandas as pd

from pysus.online_data.SINASC import download as download_sinasc
from pysus.online_data.CNES import download as download_cnes

from src.modelagem.modelo_risco_perinatal import preparar_dados


def carregar_nascimentos(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
    downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
    df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    return df


def carregar_leitos_uti_neonatal(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando CNES/ST para {uf}/{ano}...")
    downloaded = download_cnes(group='ST', states=uf, years=ano, months=12)
    df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    df['QTLEIT39'] = pd.to_numeric(df['QTLEIT39'], errors='coerce').fillna(0)
    df['CODMUN_6DIG'] = df['CODUFMUN'].astype(str).str[:6]
    leitos = df.groupby('CODMUN_6DIG')['QTLEIT39'].sum().rename('LEITOS_UTI_NEONATAL').reset_index()
    return leitos


def calcular_demanda_projetada(df_nascimentos: pd.DataFrame, caminho_modelo: Path) -> pd.DataFrame:
    modelo = joblib.load(caminho_modelo)
    X, _ = preparar_dados(df_nascimentos)
    if X.empty:
        raise ValueError("Nenhum nascimento válido após a preparação de dados.")

    scores_risco = modelo.predict_proba(X)[:, 1]
    df_com_risco = df_nascimentos.loc[X.index].copy()
    df_com_risco['SCORE_RISCO_PERINATAL'] = scores_risco
    df_com_risco['CODMUN_6DIG'] = df_com_risco['CODMUNRES'].astype(str).str[:6]

    demanda = df_com_risco.groupby('CODMUN_6DIG').agg(
        N_NASCIMENTOS=('SCORE_RISCO_PERINATAL', 'size'),
        DEMANDA_PROJETADA_ALTO_RISCO=('SCORE_RISCO_PERINATAL', 'sum'),
    ).reset_index()
    return demanda


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando nascimentos para {args.uf}/{args.ano} ---")
    df_nascimentos = carregar_nascimentos(args.uf, args.ano)
    print(f"✅ {len(df_nascimentos)} nascimentos carregados.")

    print(f"\n--- [ETAPA 2] Aplicando modelo de risco perinatal para projetar demanda ---")
    demanda = calcular_demanda_projetada(df_nascimentos, Path(args.modelo_risco))
    print(f"✅ Demanda projetada para {len(demanda)} municípios.")

    print(f"\n--- [ETAPA 3] Carregando oferta de leitos de UTI Neonatal (CNES) ---")
    oferta = carregar_leitos_uti_neonatal(args.uf, args.ano)
    print(f"✅ Oferta carregada para {len(oferta)} municípios com pelo menos 1 estabelecimento.")

    df = pd.merge(demanda, oferta, on='CODMUN_6DIG', how='left')
    df['LEITOS_UTI_NEONATAL'] = df['LEITOS_UTI_NEONATAL'].fillna(0)
    df['SCORE_PRIORIZACAO'] = df['DEMANDA_PROJETADA_ALTO_RISCO'] / (df['LEITOS_UTI_NEONATAL'] + 1)
    df = df.sort_values('SCORE_PRIORIZACAO', ascending=False)

    from src.utils.dataloaders import adicionar_nome_municipio
    df = adicionar_nome_municipio(df, 'CODMUN_6DIG', args.populacao)

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: RANKING DE PRIORIZAÇÃO DE LEITOS DE UTI NEONATAL EM {args.uf} ---")
    print("=" * 80)
    print(f"{(df['LEITOS_UTI_NEONATAL'] == 0).sum()} municípios com demanda projetada e ZERO leitos de UTI Neonatal cadastrados.")
    print("\nTop 20 municípios prioritários:")
    print(df[['CODMUN_6DIG', 'municipio', 'N_NASCIMENTOS', 'DEMANDA_PROJETADA_ALTO_RISCO', 'LEITOS_UTI_NEONATAL', 'SCORE_PRIORIZACAO']]
          .head(20).round(2).to_string(index=False))
    print("=" * 80)

    caminho_csv = dir_saida / f"ranking_uti_neonatal_{args.uf.lower()}_{args.ano}.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Ranking completo salvo em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 SCORE DE PRIORIZAÇÃO DE UTI NEONATAL CONCLUÍDO! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula um score de priorização municipal para alocação de leitos de UTI Neonatal.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--modelo-risco", type=str, default="outputs/risco_perinatal/modelo_risco_perinatal.joblib", help="Caminho para o modelo de risco perinatal treinado (modelo_risco_perinatal.py).")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada (usado para mapear nomes de município).")
    parser.add_argument("--dir_saida", type=str, default="outputs/score_uti_neonatal", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
