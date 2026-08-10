# -*- coding: utf-8 -*-
"""
======================================================================
  TAXA DE RESOLUTIVIDADE AMBULATORIAL (SIA + SIH/ICSAP)
======================================================================
Para cada município (produção pela residência do paciente, PA_MUNPCN;
internações pela residência, MUNIC_RES), relaciona o volume de
procedimentos ambulatoriais aprovados (SIA/PA) com o número de
internações evitáveis por Condições Sensíveis à Atenção Primária
(ICSAP — mesma Lista Brasileira/Portaria SAS/MS nº 221/2008 usada em
`icsap.py`; a classificação é reproduzida aqui, não importada, para
manter este módulo autossuficiente, no mesmo espírito da árvore
vendorizada em api/pipeline_indicadores/modules/features/). Quanto
maior a razão, mais atendimento ambulatorial existe para cada
internação evitável — proxy de o quanto a rede ambulatorial está
segurando a demanda antes que ela vire uma internação.
"""
import pandas as pd

from pysus.online_data.SIA import download as download_sia
from pysus.online_data.SIH import SIH

from ..utils.dataloaders import filtrar_populacao

# Lista Brasileira de ICSAP (Portaria SAS/MS nº 221/2008) — ver icsap.py
# para a documentação completa por grupo de causa.
ICSAP_BLOCOS_3CHAR = {
    "A15", "A16", "A17", "A18", "A19", "I00", "I01", "I02",
    "A51", "A52", "A53", "B50", "B51", "B52", "B53", "B54", "B55", "B56",
    "B77", "A33", "A34", "A35", "A36", "A37", "A95", "B16", "B26",
    "A00", "A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "E86",
    "D50",
    "E40", "E41", "E42", "E43", "E44", "E45", "E46",
    "E50", "E51", "E52", "E53", "E54", "E55", "E56", "E57", "E58", "E59",
    "E60", "E61", "E62", "E63", "E64",
    "H66", "J00", "J01", "J02", "J03", "J06", "J31",
    "J13", "J14",
    "J45", "J46",
    "J20", "J21", "J40", "J41", "J42", "J43", "J44", "J47",
    "I10", "I11",
    "I20",
    "I50", "J81",
    "I63", "I64", "I65", "I66", "I67", "I69", "G45", "G46",
    "E10", "E11", "E12", "E13", "E14",
    "G40", "G41",
    "N10", "N11", "N12", "N30", "N34",
    "A46", "L01", "L02", "L03", "L04", "L08",
    "N70", "N71", "N72", "N73", "N75", "N76",
    "K25", "K26", "K27", "K28",
    "O23", "A50",
}
ICSAP_CODIGOS_4CHAR = {
    "G000", "P350",
    "J153", "J154", "J158", "J159", "J181",
    "N390",
    "K920", "K921", "K922",
}


def _classificar_csap(diag_princ: pd.Series) -> pd.Series:
    codigo = diag_princ.astype(str).str.strip().str.upper()
    return codigo.str[:4].isin(ICSAP_CODIGOS_4CHAR) | codigo.str[:3].isin(ICSAP_BLOCOS_3CHAR)


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_producao_ambulatorial(uf: str, ano: int) -> pd.Series:
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
        if df_mes.empty or 'PA_MUNPCN' not in df_mes.columns:
            continue
        df_mes['PA_MUNPCN'] = df_mes['PA_MUNPCN'].astype(str).str[:6]
        for municipio, qtd in df_mes.groupby('PA_MUNPCN').size().items():
            contagens[municipio] = contagens.get(municipio, 0) + qtd

    return pd.Series(contagens, name='n_procedimentos_sia', dtype=float)


def carregar_internacoes_icsap(uf: str, ano: int) -> pd.Series:
    try:
        sih = SIH()
        sih.load()
        files = sih.get_files(group='RD', uf=uf, year=ano, month=None)
        if not files:
            return pd.Series(dtype=float, name='n_internacoes_icsap')
        parquet_set = sih.download(files)
        df_sih = pd.concat([p.to_dataframe() for p in parquet_set], ignore_index=True)
    except Exception as e:
        print(f"❌ Erro ao baixar SIH para {uf}/{ano}: {e}")
        return pd.Series(dtype=float, name='n_internacoes_icsap')

    if df_sih.empty or not {'DIAG_PRINC', 'MUNIC_RES'}.issubset(df_sih.columns):
        return pd.Series(dtype=float, name='n_internacoes_icsap')
    df_sih['MUNIC_RES'] = df_sih['MUNIC_RES'].astype(str).str.zfill(6)
    is_csap = _classificar_csap(df_sih['DIAG_PRINC'])
    return df_sih[is_csap].groupby('MUNIC_RES').size().rename('n_internacoes_icsap')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Taxa de Resolutividade Ambulatorial: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            producao_sia = carregar_producao_ambulatorial(uf, ano)
            internacoes_icsap = carregar_internacoes_icsap(uf, ano)

            df = df_base.join(producao_sia, how='left').join(internacoes_icsap, how='left')
            df[['n_procedimentos_sia', 'n_internacoes_icsap']] = df[['n_procedimentos_sia', 'n_internacoes_icsap']].fillna(0)

            df['TAXA_RESOLUTIVIDADE_AMBULATORIAL'] = df.apply(
                lambda r: (r['n_procedimentos_sia'] / r['n_internacoes_icsap']) if r['n_internacoes_icsap'] > 0 else 0, axis=1
            )

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de resolutividade ambulatorial foi processado.")
        return pd.DataFrame()

    print("✅ Taxa de Resolutividade Ambulatorial processada com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Resolutividade Ambulatorial (SIA+SIH/ICSAP) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "resolutividade_ambulatorial.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
