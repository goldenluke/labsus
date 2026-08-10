# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE DIVERSIDADE ASSISTENCIAL (CNES)
======================================================================
Para cada município, calcula a diversidade (Shannon) dos TIPOS de
estabelecimento de saúde presentes (TP_UNID do CNES/ST — ex.: UBS,
hospital geral, hospital especializado, pronto-socorro, clínica
especializada etc.), ponderada pela quantidade de cada tipo. Município
com índice alto tem uma rede variada de pontos de atenção; índice baixo
indica uma rede concentrada num único tipo de estabelecimento (ex.: só
UBS, sem retaguarda hospitalar/especializada local).
"""
import pandas as pd

from pysus.online_data.CNES import download as download_cnes

from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import calcular_diversidade


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_estabelecimentos(uf: str, ano: int) -> pd.DataFrame:
    try:
        downloaded = download_cnes(group='ST', states=uf, years=ano, months=12)
    except Exception as e:
        print(f"❌ Erro ao baixar CNES/ST para {uf}/{ano}: {e}")
        return pd.DataFrame()
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def calcular_diversidade_por_municipio(df_cnes: pd.DataFrame) -> pd.DataFrame:
    if df_cnes.empty or not {'CODUFMUN', 'TP_UNID'}.issubset(df_cnes.columns):
        return pd.DataFrame(columns=['SHANNON_DIVERSIDADE_ASSISTENCIAL', 'RIQUEZA_TIPOS_ESTABELECIMENTO'])

    df_cnes = df_cnes.copy()
    df_cnes['CODUFMUN'] = df_cnes['CODUFMUN'].astype(str).str[:6]
    df_cnes['TP_UNID'] = df_cnes['TP_UNID'].astype(str).str.zfill(2)

    linhas = []
    for municipio, grupo in df_cnes.groupby('CODUFMUN'):
        contagens = grupo['TP_UNID'].value_counts()
        d = calcular_diversidade(contagens)
        linhas.append({
            'cod_mun_ibge_6': municipio,
            'SHANNON_DIVERSIDADE_ASSISTENCIAL': d['shannon'],
            'RIQUEZA_TIPOS_ESTABELECIMENTO': d['riqueza'],
        })
    return pd.DataFrame(linhas).set_index('cod_mun_ibge_6')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Diversidade Assistencial: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_cnes = carregar_estabelecimentos(uf, ano)
            diversidade = calcular_diversidade_por_municipio(df_cnes)

            df = df_base.join(diversidade, how='left')
            df[['SHANNON_DIVERSIDADE_ASSISTENCIAL', 'RIQUEZA_TIPOS_ESTABELECIMENTO']] = df[
                ['SHANNON_DIVERSIDADE_ASSISTENCIAL', 'RIQUEZA_TIPOS_ESTABELECIMENTO']
            ].fillna(0)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de diversidade assistencial foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Diversidade Assistencial processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Diversidade Assistencial (CNES) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "diversidade_assistencial.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
