# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE CARGA HOSPITALAR POR EQUIPE DE SAÚDE DA FAMÍLIA (SIH + CNES)
======================================================================
Para cada município (pelo estabelecimento que realizou o atendimento),
calcula quantas internações (SIH) recaem sobre cada equipe de Saúde da
Família (eSF, CNES/EP, código de equipe '70') existente na região.
Mesma lógica do IND_PRESSAO_LEITOS (internações/leito), mas relativizando
pela capilaridade da atenção primária em vez da capacidade hospitalar:
valores altos sugerem que a rede de eSF local está insuficiente frente
à demanda hospitalar (associação clássica na literatura entre cobertura
de APS e desfechos hospitalares evitáveis).
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


def carregar_internacoes(uf: str, ano: int) -> pd.Series:
    try:
        downloaded = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')
    except Exception as e:
        print(f"❌ Erro ao baixar SIH para {uf}/{ano}: {e}")
        return pd.Series(dtype=float, name='n_internacoes')
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.Series(dtype=float, name='n_internacoes')
    df_sih = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    if df_sih.empty or 'MUNIC_MOV' not in df_sih.columns:
        return pd.Series(dtype=float, name='n_internacoes')
    df_sih['MUNIC_MOV'] = df_sih['MUNIC_MOV'].astype(str).str[:6]
    return df_sih.groupby('MUNIC_MOV').size().rename('n_internacoes')


def carregar_equipes_esf(uf: str, ano: int) -> pd.Series:
    try:
        downloaded = download_cnes(group='EP', states=uf, years=ano, months=12)
    except Exception as e:
        print(f"❌ Erro ao baixar CNES/EP para {uf}/{ano}: {e}")
        return pd.Series(dtype=float, name='n_equipes_esf')
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.Series(dtype=float, name='n_equipes_esf')
    df_ep = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
    if df_ep.empty or not {'TIPO_EQP', 'CODUFMUN'}.issubset(df_ep.columns):
        return pd.Series(dtype=float, name='n_equipes_esf')
    # Código '70' = Equipe de Saúde da Família (eSF) na tabela CNES/EP.
    df_esf = df_ep[df_ep['TIPO_EQP'].astype(str).str.strip() == '70'].copy()
    df_esf['CODUFMUN'] = df_esf['CODUFMUN'].astype(str).str[:6]
    if 'IDEQUIPE' in df_esf.columns:
        return df_esf.groupby('CODUFMUN')['IDEQUIPE'].nunique().rename('n_equipes_esf')
    return df_esf.groupby('CODUFMUN').size().rename('n_equipes_esf')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Carga Hospitalar por Equipe ESF: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            internacoes = carregar_internacoes(uf, ano)
            equipes_esf = carregar_equipes_esf(uf, ano)

            df = df_base.join(internacoes, how='left').join(equipes_esf, how='left')
            df[['n_internacoes', 'n_equipes_esf']] = df[['n_internacoes', 'n_equipes_esf']].fillna(0)

            df['IND_CARGA_HOSPITALAR_ESF'] = df.apply(
                lambda r: (r['n_internacoes'] / r['n_equipes_esf']) if r['n_equipes_esf'] > 0 else 0, axis=1
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de carga hospitalar por ESF foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Carga Hospitalar por Equipe ESF processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Carga Hospitalar por Equipe ESF (SIH+CNES) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "carga_hospitalar_esf.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
