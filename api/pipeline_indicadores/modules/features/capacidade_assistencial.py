# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE CAPACIDADE ASSISTENCIAL (CNES)
======================================================================
Combina quatro indicadores de oferta de recursos de saúde por município
— leitos hospitalares, médicos, enfermeiros (todos por 1.000 hab.) e
equipes de Saúde da Família (por 10.000 hab.) — num único índice 0-100
via 1ª componente principal (PCA). Não depende de linkage entre bases
nem de modelo ajustado: é uma agregação direta de campos do CNES
(snapshot de dezembro de cada ano) combinada com a população estimada.
"""
import pandas as pd

from pysus.online_data.CNES import download as download_cnes

from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import combinar_indice_composto

PREFIXO_CBO_MEDICO = '225'
PREFIXO_CBO_ENFERMEIRO = '2235'
CODIGO_TIPO_EQUIPE_ESF = '70'


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def _baixar_cnes(grupo: str, uf: str, ano: int) -> pd.DataFrame:
    try:
        downloaded = download_cnes(group=grupo, states=uf, years=ano, months=12)
    except Exception as e:
        print(f"❌ Erro ao baixar CNES/{grupo} para {uf}/{ano}: {e}")
        return pd.DataFrame()
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def calcular_componentes(uf: str, ano: int) -> pd.DataFrame:
    """Retorna um DataFrame indexado por cod_mun_ibge_6 com as contagens
    brutas de leitos, médicos, enfermeiros e equipes ESF."""
    df_st = _baixar_cnes('ST', uf, ano)
    if not df_st.empty and 'CODUFMUN' in df_st.columns and 'LEITHOSP' in df_st.columns:
        df_st['CODUFMUN'] = df_st['CODUFMUN'].astype(str).str[:6]
        leitos = pd.to_numeric(df_st['LEITHOSP'], errors='coerce').fillna(0)
        n_leitos = leitos.groupby(df_st['CODUFMUN']).sum().rename('n_leitos')
    else:
        n_leitos = pd.Series(dtype=float, name='n_leitos')

    df_pf = _baixar_cnes('PF', uf, ano)
    if not df_pf.empty and {'CODUFMUN', 'CBO', 'CPF_PROF'}.issubset(df_pf.columns):
        df_pf['CODUFMUN'] = df_pf['CODUFMUN'].astype(str).str[:6]
        df_pf['CBO'] = df_pf['CBO'].astype(str)
        df_medicos = df_pf[df_pf['CBO'].str.startswith(PREFIXO_CBO_MEDICO)]
        n_medicos = df_medicos.groupby('CODUFMUN')['CPF_PROF'].nunique().rename('n_medicos')
        df_enfermeiros = df_pf[df_pf['CBO'].str.startswith(PREFIXO_CBO_ENFERMEIRO)]
        n_enfermeiros = df_enfermeiros.groupby('CODUFMUN')['CPF_PROF'].nunique().rename('n_enfermeiros')
    else:
        n_medicos = pd.Series(dtype=float, name='n_medicos')
        n_enfermeiros = pd.Series(dtype=float, name='n_enfermeiros')

    df_ep = _baixar_cnes('EP', uf, ano)
    if not df_ep.empty and {'CODUFMUN', 'TIPO_EQP'}.issubset(df_ep.columns):
        df_ep['CODUFMUN'] = df_ep['CODUFMUN'].astype(str).str[:6]
        df_esf = df_ep[df_ep['TIPO_EQP'].astype(str).str.strip() == CODIGO_TIPO_EQUIPE_ESF]
        if 'IDEQUIPE' in df_esf.columns:
            n_equipes = df_esf.groupby('CODUFMUN')['IDEQUIPE'].nunique().rename('n_equipes_esf')
        else:
            n_equipes = df_esf.groupby('CODUFMUN').size().rename('n_equipes_esf')
    else:
        n_equipes = pd.Series(dtype=float, name='n_equipes_esf')

    componentes = pd.concat([n_leitos, n_medicos, n_enfermeiros, n_equipes], axis=1).fillna(0)
    componentes.index.name = 'cod_mun_ibge_6'
    return componentes


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Capacidade Assistencial: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            componentes = calcular_componentes(uf, ano)
            df = df_base.join(componentes, how='left').fillna(
                {'n_leitos': 0, 'n_medicos': 0, 'n_enfermeiros': 0, 'n_equipes_esf': 0}
            )

            df['TAXA_LEITOS_MIL'] = df.apply(lambda r: (r['n_leitos'] / r['populacao']) * 1000 if r['populacao'] > 0 else 0, axis=1)
            df['TAXA_MEDICOS_MIL_CAP'] = df.apply(lambda r: (r['n_medicos'] / r['populacao']) * 1000 if r['populacao'] > 0 else 0, axis=1)
            df['TAXA_ENFERMEIROS_MIL'] = df.apply(lambda r: (r['n_enfermeiros'] / r['populacao']) * 1000 if r['populacao'] > 0 else 0, axis=1)
            df['TAXA_EQUIPES_ESF_DEZ_MIL'] = df.apply(lambda r: (r['n_equipes_esf'] / r['populacao']) * 10000 if r['populacao'] > 0 else 0, axis=1)

            df['IND_CAPACIDADE_ASSISTENCIAL'] = combinar_indice_composto(
                df, ['TAXA_LEITOS_MIL', 'TAXA_MEDICOS_MIL_CAP', 'TAXA_ENFERMEIROS_MIL', 'TAXA_EQUIPES_ESF_DEZ_MIL']
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de capacidade assistencial foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Capacidade Assistencial processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Capacidade Assistencial (CNES) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "capacidade_assistencial.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
