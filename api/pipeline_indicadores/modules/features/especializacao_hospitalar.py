# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE ESPECIALIZAÇÃO HOSPITALAR (SIH)
======================================================================
Para cada município (rede hospitalar local, pelo estabelecimento que
realizou a internação), calcula o percentual das internações que
pertencem ao capítulo CID-10 mais frequente (DIAG_PRINC). Município com
índice alto tem sua produção hospitalar concentrada numa única linha de
cuidado (ex.: obstetrícia); índice baixo indica uma rede generalista,
atendendo muitas causas diferentes sem uma predominância clara.
"""
import pandas as pd

from pysus.online_data.SIH import download as download_sih

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


def calcular_especializacao(df_sih: pd.DataFrame) -> pd.DataFrame:
    if df_sih.empty or not {'MUNIC_MOV', 'DIAG_PRINC'}.issubset(df_sih.columns):
        return pd.DataFrame(columns=['IND_ESPECIALIZACAO_HOSPITALAR', 'CAPITULO_CID_PRINCIPAL_HOSP'])

    df_sih = df_sih.copy()
    df_sih['MUNIC_MOV'] = df_sih['MUNIC_MOV'].astype(str).str[:6]
    df_sih['CAPITULO_CID'] = df_sih['DIAG_PRINC'].astype(str).str[0]

    linhas = []
    for municipio, grupo in df_sih.groupby('MUNIC_MOV'):
        contagem_capitulos = grupo['CAPITULO_CID'].value_counts()
        total = contagem_capitulos.sum()
        if total == 0:
            continue
        capitulo_principal = contagem_capitulos.idxmax()
        percentual = float(contagem_capitulos.max() / total * 100)
        linhas.append({
            'cod_mun_ibge_6': municipio,
            'IND_ESPECIALIZACAO_HOSPITALAR': percentual,
            'CAPITULO_CID_PRINCIPAL_HOSP': capitulo_principal,
        })
    return pd.DataFrame(linhas).set_index('cod_mun_ibge_6')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Especialização Hospitalar: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = carregar_internacoes(uf, ano)
            especializacao = calcular_especializacao(df_sih)

            df = df_base.join(especializacao, how='left')
            df['IND_ESPECIALIZACAO_HOSPITALAR'] = df['IND_ESPECIALIZACAO_HOSPITALAR'].fillna(0)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de especialização hospitalar foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Especialização Hospitalar processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Especialização Hospitalar (SIH) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "especializacao_hospitalar.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
