# -*- coding: utf-8 -*-
"""
======================================================================
  TAXA DE MORTALIDADE GERAL (SIM)
======================================================================
Taxa bruta de mortalidade por todas as causas, por 1.000 habitantes, por
município de residência. "Tijolo" simples usado por índices compostos
de 2ª camada (src/indices/) que precisam de um desfecho de mortalidade
geral — TMI (mortalidade_infantil.py) e as taxas por causa específica
(mortalidade_causas_especificas.py) já cobrem os recortes mais finos;
este cobre o agregado bruto.
"""
import pandas as pd

from pysus.online_data.SIM import download as download_sim

from ..utils.dataloaders import filtrar_populacao


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


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


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Taxa de Mortalidade Geral: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sim = carregar_obitos(uf, ano)
            if df_sim.empty or 'CODMUNRES' not in df_sim.columns:
                obitos = pd.Series(dtype=float, name='n_obitos')
            else:
                obitos = df_sim['CODMUNRES'].astype(str).str[:6].value_counts().rename('n_obitos')
                obitos.index.name = 'cod_mun_ibge_6'

            df = df_base.join(obitos, how='left')
            df['n_obitos'] = df['n_obitos'].fillna(0)
            df['TAXA_MORTALIDADE_GERAL'] = df.apply(
                lambda r: (r['n_obitos'] / r['populacao']) * 1000 if r['populacao'] > 0 else 0, axis=1
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de mortalidade geral foi processado.")
        return pd.DataFrame()

    print("✅ Taxa de Mortalidade Geral processada com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Mortalidade Geral (SIM) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "mortalidade_geral.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
