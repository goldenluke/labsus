# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE RESOLUTIVIDADE HOSPITALAR (SIH)
======================================================================
Para cada município (rede hospitalar local, pelo estabelecimento que
realizou a internação), calcula o percentual de internações que
terminaram em alta SEM óbito (campo MORTE do SIH: 0 = alta, 1 = óbito).
Índice alto sugere uma rede resolutiva frente aos casos que atende;
índice baixo pode refletir maior gravidade dos casos recebidos ou
fragilidade assistencial — não distingue as duas causas sozinho, mas é
um primeiro sinal direto, sem exigir ajuste por casemix.
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


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Índice de Resolutividade Hospitalar: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = carregar_internacoes(uf, ano)
            if df_sih.empty or not {'MUNIC_MOV', 'MORTE'}.issubset(df_sih.columns):
                resolutividade = pd.Series(dtype=float, name='IND_RESOLUTIVIDADE')
            else:
                df_sih['MUNIC_MOV'] = df_sih['MUNIC_MOV'].astype(str).str[:6]
                df_sih['MORTE'] = pd.to_numeric(df_sih['MORTE'], errors='coerce').fillna(0)
                total = df_sih.groupby('MUNIC_MOV').size()
                altas_sem_obito = df_sih[df_sih['MORTE'] == 0].groupby('MUNIC_MOV').size()
                resolutividade = ((altas_sem_obito.reindex(total.index, fill_value=0) / total) * 100).rename('IND_RESOLUTIVIDADE')

            df = df_base.join(resolutividade, how='left')
            df['IND_RESOLUTIVIDADE'] = df['IND_RESOLUTIVIDADE'].fillna(0)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de resolutividade hospitalar foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Resolutividade Hospitalar processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Índice de Resolutividade Hospitalar (SIH) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "resolutividade_hospitalar.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
