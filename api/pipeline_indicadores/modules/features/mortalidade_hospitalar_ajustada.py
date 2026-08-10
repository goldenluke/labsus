# -*- coding: utf-8 -*-
"""
======================================================================
  ÍNDICE DE MORTALIDADE HOSPITALAR AJUSTADA POR IDADE (SIH)
======================================================================
Calcula a taxa de mortalidade intra-hospitalar (MORTE=1 / total de
internações) por município (rede local, pelo estabelecimento), primeiro
BRUTA e depois estratificada em três faixas etárias amplas (0-14, 15-59,
60+, a partir de IDADE/DIAG_PRINC). Sem ajustar por regressão, já dá
para comparar municípios de forma mais justa: a taxa PADRONIZADA aplica
a mesma distribuição etária de referência (a distribuição agregada de
internações de todo o lote de UFs/anos processado) a cada município —
padronização direta simples, elimina boa parte do efeito de municípios
terem perfis etários de pacientes internados muito diferentes.
"""
import pandas as pd

from pysus.online_data.SIH import download as download_sih

from ..utils.dataloaders import filtrar_populacao

FAIXAS = [(0, 14, '0_14'), (15, 59, '15_59'), (60, 130, '60_MAIS')]


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


def _classificar_faixa(idade):
    for minimo, maximo, rotulo in FAIXAS:
        if minimo <= idade <= maximo:
            return rotulo
    return None


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    dfs_sih_por_periodo = {}
    for uf in ufs:
        for ano in anos:
            df_sih = carregar_internacoes(uf, ano)
            dfs_sih_por_periodo[(uf, ano)] = df_sih

    # Distribuição etária de referência: agregada de TODO o lote processado
    # (todas as UFs/anos desta execução), usada como padrão de comparação.
    todas_internacoes = [df for df in dfs_sih_por_periodo.values() if not df.empty and {'IDADE', 'MUNIC_MOV', 'MORTE'}.issubset(df.columns)]
    if todas_internacoes:
        df_ref = pd.concat(todas_internacoes, ignore_index=True)
        df_ref['FAIXA_ETARIA'] = pd.to_numeric(df_ref['IDADE'], errors='coerce').apply(
            lambda x: _classificar_faixa(x) if pd.notna(x) else None
        )
        pesos_referencia = df_ref['FAIXA_ETARIA'].value_counts(normalize=True).to_dict()
    else:
        pesos_referencia = {}

    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Mortalidade Hospitalar Ajustada: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = dfs_sih_por_periodo.get((uf, ano), pd.DataFrame())
            colunas_saida = ['TMH_HOSPITALAR', 'TMH_HOSP_0_14', 'TMH_HOSP_15_59', 'TMH_HOSP_60_MAIS', 'TMH_HOSPITALAR_PADRONIZADA']

            if df_sih.empty or not {'IDADE', 'MUNIC_MOV', 'MORTE'}.issubset(df_sih.columns):
                indicadores = pd.DataFrame(columns=colunas_saida)
            else:
                df_sih = df_sih.copy()
                df_sih['MUNIC_MOV'] = df_sih['MUNIC_MOV'].astype(str).str[:6]
                df_sih['MORTE'] = pd.to_numeric(df_sih['MORTE'], errors='coerce').fillna(0)
                df_sih['FAIXA_ETARIA'] = pd.to_numeric(df_sih['IDADE'], errors='coerce').apply(
                    lambda x: _classificar_faixa(x) if pd.notna(x) else None
                )

                linhas = []
                for municipio, grupo in df_sih.groupby('MUNIC_MOV'):
                    total = len(grupo)
                    tmh_bruta = float(grupo['MORTE'].mean() * 100) if total > 0 else 0.0

                    taxas_faixa = {}
                    for _, _, rotulo in FAIXAS:
                        sub = grupo[grupo['FAIXA_ETARIA'] == rotulo]
                        taxas_faixa[rotulo] = float(sub['MORTE'].mean() * 100) if len(sub) > 0 else 0.0

                    tmh_padronizada = sum(
                        taxas_faixa[rotulo] * pesos_referencia.get(rotulo, 0.0) for _, _, rotulo in FAIXAS
                    )

                    linhas.append({
                        'cod_mun_ibge_6': municipio,
                        'TMH_HOSPITALAR': tmh_bruta,
                        'TMH_HOSP_0_14': taxas_faixa['0_14'],
                        'TMH_HOSP_15_59': taxas_faixa['15_59'],
                        'TMH_HOSP_60_MAIS': taxas_faixa['60_MAIS'],
                        'TMH_HOSPITALAR_PADRONIZADA': tmh_padronizada,
                    })
                indicadores = pd.DataFrame(linhas).set_index('cod_mun_ibge_6')

            df = df_base.join(indicadores, how='left')
            df[colunas_saida] = df[colunas_saida].fillna(0)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de mortalidade hospitalar ajustada foi processado.")
        return pd.DataFrame()

    print("✅ Índice de Mortalidade Hospitalar Ajustada processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula a Mortalidade Hospitalar Ajustada por Idade (SIH) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "mortalidade_hospitalar_ajustada.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
