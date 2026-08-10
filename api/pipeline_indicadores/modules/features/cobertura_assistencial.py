# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE COBERTURA ASSISTENCIAL (CNES)
======================================================================
Diferente do "Índice de Capacidade Assistencial" (que mede a INTENSIDADE
de recursos — leitos/médicos/enfermeiros/equipes por habitante), este
mede a AMPLITUDE da rede de pontos de assistência presentes no
município — nº de UBS e nº de hospitais por habitante — combinada com a
cobertura de equipes de Saúde da Família. Município pode ter poucos
pontos mas bem equipados (alta capacidade, baixa cobertura) ou muitos
pontos pequenos (baixa capacidade, alta cobertura); os dois índices
respondem perguntas de planejamento diferentes.
"""
import pandas as pd

from pysus.online_data.CNES import download as download_cnes

from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import combinar_indice_composto

TIPOS_UNIDADE_UBS = ('01', '02')  # Posto de Saúde, Centro de Saúde/UBS
TIPOS_UNIDADE_HOSPITAL = ('05', '07')  # Hospital Geral, Hospital Especializado
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
    df_st = _baixar_cnes('ST', uf, ano)
    if not df_st.empty and {'CODUFMUN', 'TP_UNID'}.issubset(df_st.columns):
        df_st['CODUFMUN'] = df_st['CODUFMUN'].astype(str).str[:6]
        df_st['TP_UNID'] = df_st['TP_UNID'].astype(str).str.zfill(2)
        n_ubs = df_st[df_st['TP_UNID'].isin(TIPOS_UNIDADE_UBS)].groupby('CODUFMUN').size().rename('n_ubs')
        n_hospitais = df_st[df_st['TP_UNID'].isin(TIPOS_UNIDADE_HOSPITAL)].groupby('CODUFMUN').size().rename('n_hospitais')
    else:
        n_ubs = pd.Series(dtype=float, name='n_ubs')
        n_hospitais = pd.Series(dtype=float, name='n_hospitais')

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

    componentes = pd.concat([n_ubs, n_hospitais, n_equipes], axis=1).fillna(0)
    componentes.index.name = 'cod_mun_ibge_6'
    return componentes


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Cobertura Assistencial: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            componentes = calcular_componentes(uf, ano)
            df = df_base.join(componentes, how='left').fillna(
                {'n_ubs': 0, 'n_hospitais': 0, 'n_equipes_esf': 0}
            )

            df['TAXA_UBS_DEZ_MIL'] = df.apply(lambda r: (r['n_ubs'] / r['populacao']) * 10000 if r['populacao'] > 0 else 0, axis=1)
            df['TAXA_HOSPITAIS_CEM_MIL'] = df.apply(lambda r: (r['n_hospitais'] / r['populacao']) * 100000 if r['populacao'] > 0 else 0, axis=1)
            df['TAXA_EQUIPES_ESF_DEZ_MIL_COB'] = df.apply(lambda r: (r['n_equipes_esf'] / r['populacao']) * 10000 if r['populacao'] > 0 else 0, axis=1)

            df['IND_COBERTURA_ASSISTENCIAL'] = combinar_indice_composto(
                df, ['TAXA_UBS_DEZ_MIL', 'TAXA_HOSPITAIS_CEM_MIL', 'TAXA_EQUIPES_ESF_DEZ_MIL_COB']
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de cobertura assistencial foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Cobertura Assistencial processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Cobertura Assistencial (CNES) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "cobertura_assistencial.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
