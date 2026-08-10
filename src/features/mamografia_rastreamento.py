# -*- coding: utf-8 -*-
"""
======================================================================
  TAXA DE COBERTURA DE MAMOGRAFIA DE RASTREAMENTO (SIA)
======================================================================
Conta, por município de residência da paciente (PA_MUNPCN), as
mamografias bilaterais de RASTREAMENTO aprovadas no SIA/PA — código
SIGTAP 0204030188 (grupo 02: Procedimentos com finalidade
diagnóstica; subgrupo 04: Diagnóstico por Radiologia), o mesmo
procedimento usado pelo indicador RIPSA/INCA/Previne Brasil de
cobertura de rastreamento do câncer de mama. Diferente desse
indicador oficial (que usa como denominador a população feminina de
50-69 anos), aqui a taxa é por população TOTAL do município — a mesma
convenção usada pelos demais indicadores deste projeto (ver
`icsap.py`, `internacoes_gerais.py`), já que não há projeção
populacional por sexo/idade disponível localmente.
"""
import pandas as pd

from pysus.online_data.SIA import download as download_sia

from ..utils.dataloaders import filtrar_populacao

CODIGO_SIGTAP_RASTREAMENTO = '0204030188'


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_mamografias(uf: str, ano: int) -> pd.Series:
    """SIA é baixado mês a mês (competência mensal), diferente do SIH/SINASC/SIM."""
    contagens = {}
    for mes in range(1, 13):
        try:
            downloaded = download_sia(states=uf, years=ano, months=mes, groups=['PA'])
        except Exception as e:
            print(f"❌ Erro ao baixar SIA/PA para {uf}/{ano}-{mes:02d}: {e}")
            continue
        arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
        if not arquivos:
            continue
        df_mes = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
        if df_mes.empty or not {'PA_MUNPCN', 'PA_PROC_ID'}.issubset(df_mes.columns):
            continue
        df_mes['PA_PROC_ID'] = df_mes['PA_PROC_ID'].astype(str).str.strip()
        df_rastreamento = df_mes[df_mes['PA_PROC_ID'] == CODIGO_SIGTAP_RASTREAMENTO]
        if df_rastreamento.empty:
            continue
        df_rastreamento = df_rastreamento.assign(PA_MUNPCN=df_rastreamento['PA_MUNPCN'].astype(str).str[:6])
        for municipio, qtd in df_rastreamento.groupby('PA_MUNPCN').size().items():
            contagens[municipio] = contagens.get(municipio, 0) + qtd

    return pd.Series(contagens, name='n_mamografias', dtype=float)


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Taxa de Cobertura de Mamografia de Rastreamento: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            mamografias = carregar_mamografias(uf, ano)

            df = df_base.join(mamografias, how='left')
            df['n_mamografias'] = df['n_mamografias'].fillna(0)
            df['TAXA_COBERTURA_MAMOGRAFIA'] = (df['n_mamografias'] / df['populacao']) * 1000

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de cobertura de mamografia foi processado.")
        return pd.DataFrame()

    print("✅ Taxa de Cobertura de Mamografia de Rastreamento processada com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Cobertura de Mamografia de Rastreamento (SIA/PA) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "mamografia_rastreamento.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
