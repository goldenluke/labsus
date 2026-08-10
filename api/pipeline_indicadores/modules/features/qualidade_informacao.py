# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE QUALIDADE DA INFORMAÇÃO (SIM + SINASC)
======================================================================
Para cada município (de residência), mede o quão completos estão os
registros do SIM (óbitos) e do SINASC (nascidos vivos) em quatro campos
sociodemográficos básicos — idade, sexo, raça/cor e escolaridade —
contando o percentual de registros em branco ou com o código "ignorado"
(9, convenção DATASUS para campos categóricos). Índice = 100 - %problema,
por sistema e campo, mais uma média geral. Serve como um proxy direto
da confiabilidade de qualquer indicador derivado desses sistemas para
aquele município: se a informação de base está mal preenchida, qualquer
indicador construído em cima dela (TMI, cesáreas, mortalidade por causa
específica etc.) deve ser interpretado com mais cautela ali.
"""
import pandas as pd

from pysus.online_data.SIM import download as download_sim
from pysus.online_data.SINASC import download as download_sinasc

from ..utils.dataloaders import filtrar_populacao

CODIGO_IGNORADO = '9'


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def _percentual_problematico(serie: pd.Series) -> pd.Series:
    """1 se o valor está em branco/nulo OU é o código 'ignorado' (9), senão 0."""
    valores = serie.astype(str).str.strip()
    return ((serie.isna()) | (valores == '') | (valores == CODIGO_IGNORADO) | (valores == '9.0')).astype(int)


def _iqi_por_municipio(df: pd.DataFrame, coluna_municipio: str, campos: dict, sufixo: str) -> pd.DataFrame:
    """campos: {NOME_SAIDA: coluna_no_df}. Retorna 100 - %problemático por campo + média geral."""
    if df.empty or coluna_municipio not in df.columns:
        colunas_vazias = [f'{nome}_{sufixo}' for nome in campos] + [f'IQI_GERAL_{sufixo}']
        return pd.DataFrame(columns=colunas_vazias)

    df = df.copy()
    df[coluna_municipio] = df[coluna_municipio].astype(str).str[:6]

    resultado = pd.DataFrame({'cod_mun_ibge_6': df[coluna_municipio]})
    nomes_colunas = []
    for nome_saida, coluna in campos.items():
        col_final = f'{nome_saida}_{sufixo}'
        nomes_colunas.append(col_final)
        if coluna in df.columns:
            resultado[col_final] = 100 - _percentual_problematico(df[coluna]) * 100
        else:
            resultado[col_final] = 100

    agregado = resultado.groupby('cod_mun_ibge_6')[nomes_colunas].mean()
    agregado[f'IQI_GERAL_{sufixo}'] = agregado[nomes_colunas].mean(axis=1)
    return agregado


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


def carregar_nascimentos(uf: str, ano: int) -> pd.DataFrame:
    try:
        downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
    except Exception as e:
        print(f"❌ Erro ao baixar SINASC para {uf}/{ano}: {e}")
        return pd.DataFrame()
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Qualidade da Informação: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_obitos = carregar_obitos(uf, ano)
            iqi_sim = _iqi_por_municipio(
                df_obitos, 'CODMUNRES',
                {'IQI_IDADE': 'IDADE', 'IQI_SEXO': 'SEXO', 'IQI_RACA': 'RACACOR', 'IQI_ESCOLARIDADE': 'ESC'},
                'SIM',
            )

            df_nascimentos = carregar_nascimentos(uf, ano)
            iqi_sinasc = _iqi_por_municipio(
                df_nascimentos, 'CODMUNRES',
                {'IQI_IDADE': 'IDADEMAE', 'IQI_SEXO': 'SEXO', 'IQI_RACA': 'RACACORMAE', 'IQI_ESCOLARIDADE': 'ESCMAE2010'},
                'SINASC',
            )

            df = df_base.join(iqi_sim, how='left').join(iqi_sinasc, how='left')
            colunas_indicadores = [c for c in df.columns if c.startswith('IQI_')]
            df[colunas_indicadores] = df[colunas_indicadores].fillna(100)
            df['IQI_QUALIDADE_INFORMACAO'] = df[['IQI_GERAL_SIM', 'IQI_GERAL_SINASC']].mean(axis=1)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de qualidade da informação foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Qualidade da Informação processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Qualidade da Informação (SIM+SINASC) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "qualidade_informacao.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
