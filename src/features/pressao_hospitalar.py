# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE PRESSÃO HOSPITALAR (SIH + CNES)
======================================================================
Para cada município (rede hospitalar local, pelo estabelecimento que
realizou a internação), calcula duas razões simples de pressão sobre a
capacidade instalada: internações por leito e dias de permanência
totais por leito, no período. Valores altos indicam uma rede hospitalar
sob alta rotatividade/ocupação frente ao nº de leitos disponíveis.
"""
import pandas as pd

from pysus.online_data.SIH import download as download_sih
from pysus.online_data.CNES import download as download_cnes

from ..utils.dataloaders import filtrar_populacao


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


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


def carregar_leitos(uf: str, ano: int) -> pd.Series:
    try:
        downloaded = download_cnes(group='ST', states=uf, years=ano, months=12)
    except Exception as e:
        print(f"❌ Erro ao baixar CNES/ST para {uf}/{ano}: {e}")
        return pd.Series(dtype=float, name='n_leitos')
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.Series(dtype=float, name='n_leitos')
    df_st = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    if df_st.empty or not {'CODUFMUN', 'LEITHOSP'}.issubset(df_st.columns):
        return pd.Series(dtype=float, name='n_leitos')
    df_st['CODUFMUN'] = df_st['CODUFMUN'].astype(str).str[:6]
    leitos = pd.to_numeric(df_st['LEITHOSP'], errors='coerce').fillna(0)
    return leitos.groupby(df_st['CODUFMUN']).sum().rename('n_leitos')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Pressão Hospitalar: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = carregar_internacoes(uf, ano)
            if df_sih.empty or not {'MUNIC_MOV', 'DIAS_PERM'}.issubset(df_sih.columns):
                internacoes = pd.Series(dtype=float, name='n_internacoes')
                dias_perm = pd.Series(dtype=float, name='total_dias_perm')
            else:
                df_sih['MUNIC_MOV'] = df_sih['MUNIC_MOV'].astype(str).str[:6]
                internacoes = df_sih.groupby('MUNIC_MOV').size().rename('n_internacoes')
                dias_perm = pd.to_numeric(df_sih['DIAS_PERM'], errors='coerce').fillna(0).groupby(df_sih['MUNIC_MOV']).sum().rename('total_dias_perm')

            leitos = carregar_leitos(uf, ano)

            df = df_base.join(internacoes, how='left').join(dias_perm, how='left').join(leitos, how='left')
            df[['n_internacoes', 'total_dias_perm', 'n_leitos']] = df[['n_internacoes', 'total_dias_perm', 'n_leitos']].fillna(0)

            df['IND_PRESSAO_LEITOS'] = df.apply(
                lambda r: (r['n_internacoes'] / r['n_leitos']) if r['n_leitos'] > 0 else 0, axis=1
            )
            df['IND_PRESSAO_PERMANENCIA'] = df.apply(
                lambda r: (r['total_dias_perm'] / r['n_leitos']) if r['n_leitos'] > 0 else 0, axis=1
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de pressão hospitalar foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Pressão Hospitalar processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Pressão Hospitalar (SIH+CNES) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "pressao_hospitalar.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
