# -*- coding: utf-8 -*-
"""
======================================================================
  ADEQUAÇÃO DE UTI NEONATAL À DEMANDA DE ALTO RISCO (SINASC + CNES)
======================================================================
Para cada município (nascimentos pela residência da mãe; leitos pelo
estabelecimento), relaciona o volume de nascidos vivos de baixo peso
(<2.500g, campo PESO do SINASC — proxy padrão de risco neonatal) com o
número de leitos de UTI Neonatal instalados na região (CNES/LT, códigos
80/81/82 = UTI Neonatal Tipo I/II/III, conforme a Tabela de Tipo de
Leito do CNES). Valores altos indicam demanda de alto risco
desproporcional à infraestrutura neonatal intensiva disponível
localmente.
"""
import pandas as pd

from pysus.online_data.SINASC import download as download_sinasc
from pysus.online_data.CNES import download as download_cnes

from ..utils.dataloaders import filtrar_populacao

CODIGOS_UTI_NEONATAL = {'80', '81', '82'}  # UTI Neonatal Tipo I, II e III
LIMIAR_BAIXO_PESO_G = 2500


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_nascidos_baixo_peso(uf: str, ano: int) -> pd.Series:
    try:
        downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
    except Exception as e:
        print(f"❌ Erro ao baixar SINASC para {uf}/{ano}: {e}")
        return pd.Series(dtype=float, name='n_baixo_peso')
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.Series(dtype=float, name='n_baixo_peso')
    df_sinasc = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    if df_sinasc.empty or not {'CODMUNRES', 'PESO'}.issubset(df_sinasc.columns):
        return pd.Series(dtype=float, name='n_baixo_peso')
    df_sinasc['CODMUNRES'] = df_sinasc['CODMUNRES'].astype(str).str[:6]
    peso = pd.to_numeric(df_sinasc['PESO'], errors='coerce')
    df_baixo_peso = df_sinasc[peso < LIMIAR_BAIXO_PESO_G]
    return df_baixo_peso.groupby('CODMUNRES').size().rename('n_baixo_peso')


def carregar_leitos_uti_neonatal(uf: str, ano: int) -> pd.Series:
    try:
        downloaded = download_cnes(group='LT', states=uf, years=ano, months=12)
    except Exception as e:
        print(f"❌ Erro ao baixar CNES/LT para {uf}/{ano}: {e}")
        return pd.Series(dtype=float, name='n_leitos_uti_neonatal')
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.Series(dtype=float, name='n_leitos_uti_neonatal')
    df_lt = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    if df_lt.empty or not {'CODLEITO', 'CODUFMUN', 'QT_SUS'}.issubset(df_lt.columns):
        return pd.Series(dtype=float, name='n_leitos_uti_neonatal')
    df_lt['CODUFMUN'] = df_lt['CODUFMUN'].astype(str).str[:6]
    df_uti = df_lt[df_lt['CODLEITO'].astype(str).str.strip().isin(CODIGOS_UTI_NEONATAL)].copy()
    leitos = pd.to_numeric(df_uti['QT_SUS'], errors='coerce').fillna(0)
    return leitos.groupby(df_uti['CODUFMUN']).sum().rename('n_leitos_uti_neonatal')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Adequação de UTI Neonatal: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            baixo_peso = carregar_nascidos_baixo_peso(uf, ano)
            leitos_uti = carregar_leitos_uti_neonatal(uf, ano)

            df = df_base.join(baixo_peso, how='left').join(leitos_uti, how='left')
            df[['n_baixo_peso', 'n_leitos_uti_neonatal']] = df[['n_baixo_peso', 'n_leitos_uti_neonatal']].fillna(0)

            df['IND_ADEQUACAO_UTI_NEONATAL'] = df.apply(
                lambda r: (r['n_baixo_peso'] / r['n_leitos_uti_neonatal']) if r['n_leitos_uti_neonatal'] > 0 else 0, axis=1
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de adequação de UTI neonatal foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Adequação de UTI Neonatal processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Adequação de UTI Neonatal (SINASC+CNES) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "adequacao_uti_neonatal.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
