# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE COMPLEXIDADE HOSPITALAR (SIH)
======================================================================
Para cada município (rede hospitalar local agregada, pelo estabelecimento
que realizou a internação), calcula três medidas diretas de complexidade
assistencial a partir do SIH — nº de procedimentos distintos realizados
(PROC_REA), nº de capítulos CID-10 distintos tratados (DIAG_PRINC) e nº
total de internações — e combina as três num índice 0-100 (PCA). Nenhum
linkage entre bases: é uma contagem direta por município de ocorrência.
"""
import pandas as pd

from pysus.online_data.SIH import download as download_sih

from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import combinar_indice_composto


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


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Complexidade Hospitalar: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = carregar_internacoes(uf, ano)
            if df_sih.empty or not {'MUNIC_MOV', 'PROC_REA', 'DIAG_PRINC'}.issubset(df_sih.columns):
                print(f"⚠️ Sem dados SIH suficientes para {uf}/{ano}.")
                componentes = pd.DataFrame(columns=['n_internacoes', 'n_proc_distintos', 'n_capitulos_cid'])
            else:
                df_sih['MUNIC_MOV'] = df_sih['MUNIC_MOV'].astype(str).str[:6]
                df_sih['CAPITULO_CID'] = df_sih['DIAG_PRINC'].astype(str).str[0]

                n_internacoes = df_sih.groupby('MUNIC_MOV').size().rename('n_internacoes')
                n_proc_distintos = df_sih.groupby('MUNIC_MOV')['PROC_REA'].nunique().rename('n_proc_distintos')
                n_capitulos_cid = df_sih.groupby('MUNIC_MOV')['CAPITULO_CID'].nunique().rename('n_capitulos_cid')
                componentes = pd.concat([n_internacoes, n_proc_distintos, n_capitulos_cid], axis=1)
                componentes.index.name = 'cod_mun_ibge_6'

            df = df_base.join(componentes, how='left').fillna(
                {'n_internacoes': 0, 'n_proc_distintos': 0, 'n_capitulos_cid': 0}
            )
            df = df.rename(columns={
                'n_internacoes': 'N_INTERNACOES_HOSP',
                'n_proc_distintos': 'N_PROC_DISTINTOS_HOSP',
                'n_capitulos_cid': 'N_CAPITULOS_CID_HOSP',
            })

            df['IND_COMPLEXIDADE_HOSPITALAR'] = combinar_indice_composto(
                df, ['N_INTERNACOES_HOSP', 'N_PROC_DISTINTOS_HOSP', 'N_CAPITULOS_CID_HOSP']
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de complexidade hospitalar foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Complexidade Hospitalar processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Complexidade Hospitalar (SIH) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "complexidade_hospitalar.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
