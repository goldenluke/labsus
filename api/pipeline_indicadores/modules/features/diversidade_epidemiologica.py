# -*- coding: utf-8 -*-
"""
======================================================================
  DIVERSIDADE EPIDEMIOLÓGICA (SIM + SIH)
======================================================================
Para cada município (de residência), calcula a diversidade das causas de
óbito (SIM/CAUSABAS) e das causas de internação (SIH/DIAG_PRINC) usando
os índices de Shannon (H') e Simpson (1-D), além da riqueza (nº de CID-10
distintos observados). Município com diversidade alta tem uma carga de
doenças espalhada por muitas causas diferentes; diversidade baixa indica
concentração num pequeno número de causas dominantes. Nenhum linkage
entre bases — cada sistema é agregado independentemente por município.
"""
import pandas as pd

from pysus.online_data.SIM import download as download_sim
from pysus.online_data.SIH import download as download_sih

from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import calcular_diversidade


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def _diversidade_por_municipio(df: pd.DataFrame, coluna_municipio: str, coluna_cid: str, sufixo: str) -> pd.DataFrame:
    if df.empty or coluna_municipio not in df.columns or coluna_cid not in df.columns:
        return pd.DataFrame(columns=[f'SHANNON_DIVERSIDADE_{sufixo}', f'SIMPSON_DIVERSIDADE_{sufixo}', f'RIQUEZA_CID_{sufixo}'])

    df = df.copy()
    df[coluna_municipio] = df[coluna_municipio].astype(str).str[:6]
    df['CID3'] = df[coluna_cid].astype(str).str[:3]

    linhas = []
    for municipio, grupo in df.groupby(coluna_municipio):
        contagens = grupo['CID3'].value_counts()
        d = calcular_diversidade(contagens)
        linhas.append({
            'cod_mun_ibge_6': municipio,
            f'SHANNON_DIVERSIDADE_{sufixo}': d['shannon'],
            f'SIMPSON_DIVERSIDADE_{sufixo}': d['simpson'],
            f'RIQUEZA_CID_{sufixo}': d['riqueza'],
        })
    return pd.DataFrame(linhas).set_index('cod_mun_ibge_6')


def carregar_obitos(uf: str, ano: int) -> pd.DataFrame:
    try:
        downloaded = download_sim(states=uf, years=ano, groups=['CID10'])
    except Exception as e:
        print(f"❌ Erro ao baixar SIM para {uf}/{ano}: {e}")
        return pd.DataFrame()
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def carregar_internacoes(uf: str, ano: int) -> pd.DataFrame:
    try:
        downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
    except Exception as e:
        print(f"❌ Erro ao baixar SIH para {uf}/{ano}: {e}")
        return pd.DataFrame()
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Diversidade Epidemiológica: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_obitos = carregar_obitos(uf, ano)
            diversidade_obitos = _diversidade_por_municipio(df_obitos, 'CODMUNRES', 'CAUSABAS', 'OBITOS')

            df_internacoes = carregar_internacoes(uf, ano)
            diversidade_internacoes = _diversidade_por_municipio(df_internacoes, 'MUNIC_RES', 'DIAG_PRINC', 'INTERNACOES')

            df = df_base.join(diversidade_obitos, how='left').join(diversidade_internacoes, how='left')
            colunas_indicadores = [
                'SHANNON_DIVERSIDADE_OBITOS', 'SIMPSON_DIVERSIDADE_OBITOS', 'RIQUEZA_CID_OBITOS',
                'SHANNON_DIVERSIDADE_INTERNACOES', 'SIMPSON_DIVERSIDADE_INTERNACOES', 'RIQUEZA_CID_INTERNACOES',
            ]
            df[colunas_indicadores] = df[colunas_indicadores].fillna(0)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de diversidade epidemiológica foi processado.")
        return pd.DataFrame()

    print("✅ Diversidade Epidemiológica processada com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula a Diversidade Epidemiológica (Shannon/Simpson) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "diversidade_epidemiologica.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
