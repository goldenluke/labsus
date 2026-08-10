# -*- coding: utf-8 -*-
"""
======================================================================
  REGRESSÃO BINOMIAL NEGATIVA: DETERMINANTES DA TAXA DE INTERNAÇÃO
======================================================================
Contagens de internação por município (poucos casos em municípios
pequenos, muitos em grandes) violam as premissas de uma regressão linear
comum: a variância cresce com a média e costuma ser MAIOR do que a média
(superdispersão) — um Poisson simples já subestimaria os erros-padrão.
Este script ajusta um Modelo Linear Generalizado (GLM) Binomial Negativo
(statsmodels), o padrão-ouro para dados de contagem superdispersos em
epidemiologia, para estimar como a vulnerabilidade social (IVS) e a
densidade de Unidades Básicas de Saúde (UBS) afetam a taxa de internação
por uma causa configurável — com a população como "exposure" (offset em
log), transformando o modelo de contagem em, efetivamente, um modelo de
TAXA.

Resultado interpretável em Razão de Taxas de Incidência (IRR): "cada
unidade a mais de IVS multiplica a taxa de internação por X".
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from pysus.online_data.SIH import download as download_sih
from pysus.online_data.CNES import download as download_cnes


def carregar_ivs(diretorio_ivs: Path, ufs: list) -> pd.DataFrame:
    dfs = []
    for uf in ufs:
        for candidato in [diretorio_ivs / f"ivs_{uf.lower()}.csv", diretorio_ivs / f"ivs_{uf.upper()}.csv"]:
            if candidato.exists():
                dfs.append(pd.read_csv(candidato))
                break
    if not dfs:
        raise FileNotFoundError(f"Nenhum arquivo de IVS encontrado em '{diretorio_ivs}' para {ufs}.")
    df_ivs = pd.concat(dfs, ignore_index=True)
    col_mun = next((c for c in ['municipio', 'codmun7', 'Codmun', 'codigo_ibge', 'cod_mun', 'codmun'] if c in df_ivs.columns), None)
    if col_mun is None:
        raise KeyError("Nenhuma coluna de código de município encontrada no CSV do IVS.")
    df_ivs['cod_mun_ibge_6'] = df_ivs[col_mun].astype(str).str[:6]
    return df_ivs[['cod_mun_ibge_6', 'ivs']].dropna().drop_duplicates(subset=['cod_mun_ibge_6'])


def carregar_ubs_por_municipio(ufs: list, ano: int) -> pd.DataFrame:
    downloaded = download_cnes(group='ST', states=ufs, years=ano, months=12)
    df_cnes = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    df_ubs = df_cnes[df_cnes['TP_UNID'] == '02'].copy()
    contagem = df_ubs.groupby('CODUFMUN').size().rename('N_UBS').reset_index()
    contagem.rename(columns={'CODUFMUN': 'cod_mun_ibge_6'}, inplace=True)
    contagem['cod_mun_ibge_6'] = contagem['cod_mun_ibge_6'].astype(str)
    return contagem


def carregar_internacoes(ufs: list, ano: int, cid_prefixos: list) -> pd.DataFrame:
    downloaded = download_sih(states=ufs, years=ano, months=list(range(1, 13)), groups='RD')
    df_sih = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    df_diag = df_sih[df_sih['DIAG_PRINC'].astype(str).str.startswith(tuple(cid_prefixos))].copy()
    df_diag['cod_mun_ibge_6'] = df_diag['MUNIC_RES'].astype(str).str[:6]
    casos = df_diag.groupby('cod_mun_ibge_6').size().rename('N_INTERNACOES').reset_index()
    return casos


def montar_dataset(ufs: list, ano: int, cid_prefixos: list, diretorio_ivs: Path, arquivo_populacao: Path) -> pd.DataFrame:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.dataloaders import filtrar_populacao

    print("[LOG] Carregando IVS...")
    df_ivs = carregar_ivs(diretorio_ivs, ufs)
    print("[LOG] Carregando contagem de UBS (CNES)...")
    df_ubs = carregar_ubs_por_municipio(ufs, ano)
    print("[LOG] Carregando internações (SIH)...")
    df_int = carregar_internacoes(ufs, ano, cid_prefixos)

    dfs_pop = []
    for uf in ufs:
        df_pop_uf = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
        if df_pop_uf is not None:
            dfs_pop.append(df_pop_uf.reset_index().rename(columns={'index': 'cod_mun_ibge_6'}))
    if not dfs_pop:
        raise ValueError("Nenhum dado de população encontrado para as UFs informadas.")
    df_pop = pd.concat(dfs_pop, ignore_index=True)

    df = df_pop[['cod_mun_ibge_6', 'municipio', 'populacao', 'UF']].copy()
    df = df.merge(df_ivs, on='cod_mun_ibge_6', how='left')
    df = df.merge(df_ubs, on='cod_mun_ibge_6', how='left')
    df = df.merge(df_int, on='cod_mun_ibge_6', how='left')
    df['N_INTERNACOES'] = df['N_INTERNACOES'].fillna(0)
    df['N_UBS'] = df['N_UBS'].fillna(0)
    df['DENSIDADE_UBS_10K'] = (df['N_UBS'] / df['populacao']) * 10000
    df = df.dropna(subset=['ivs', 'populacao'])
    df = df[df['populacao'] > 0]
    return df


def ajustar_binomial_negativa(df: pd.DataFrame):
    df = df.copy()
    df['log_populacao'] = np.log(df['populacao'])
    modelo = smf.glm(
        formula='N_INTERNACOES ~ ivs + DENSIDADE_UBS_10K',
        data=df,
        family=sm.families.NegativeBinomial(),
        offset=df['log_populacao'],
    ).fit()
    return modelo


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    cid_nome = "-".join(args.cids)

    print(f"\n--- [ETAPA 1] Montando dataset municipal para {args.ufs}/{args.ano} ({cid_nome}) ---")
    df = montar_dataset(args.ufs, args.ano, args.cids, Path(args.ivs_dir), Path(args.populacao))
    print(f"✅ Dataset com {len(df)} municípios.")

    if len(df) < 15:
        print("❌ Poucos municípios para uma regressão confiável (mínimo recomendado: 15).")
        return

    print(f"\n--- [ETAPA 2] Ajustando GLM Binomial Negativo ---")
    modelo = ajustar_binomial_negativa(df)
    print("✅ Modelo ajustado com sucesso.")

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: DETERMINANTES DA TAXA DE INTERNAÇÃO POR '{cid_nome}' ---")
    print("=" * 80)
    print(modelo.summary())

    irr = np.exp(modelo.params)
    ic = np.exp(modelo.conf_int())
    tabela_irr = pd.DataFrame({
        'coeficiente': modelo.params, 'IRR (Razão de Taxas)': irr,
        'IC95_inferior': ic[0], 'IC95_superior': ic[1], 'p_valor': modelo.pvalues,
    })
    print("\n--- Razões de Taxas de Incidência (IRR) ---")
    print(tabela_irr.to_string())
    print("=" * 80)

    caminho_csv = dir_saida / f"binomial_negativa_{cid_nome.lower()}_{args.ano}.csv"
    tabela_irr.to_csv(caminho_csv, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Tabela de resultados salva em: '{caminho_csv}'")

    df['PREDITO'] = modelo.predict(df)
    caminho_dados = dir_saida / f"dados_com_predicao_{cid_nome.lower()}_{args.ano}.csv"
    df.to_csv(caminho_dados, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Dados municipais com valores preditos salvos em: '{caminho_dados}'")

    print("\n" + "=" * 80)
    print("🎉 REGRESSÃO BINOMIAL NEGATIVA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ajusta um GLM Binomial Negativo para determinantes da taxa de internação municipal.")
    parser.add_argument("--ufs", nargs="+", required=True, help="Lista de UFs a processar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--cids", nargs="+", default=['J45'], help="Prefixos de CID-10 a considerar (ex: J45 para asma).")
    parser.add_argument("--ivs-dir", type=str, default="referencia/ipea", help="Diretório com os arquivos CSV do IVS por estado.")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada.")
    parser.add_argument("--dir_saida", type=str, default="outputs/binomial_negativa_internacao", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
