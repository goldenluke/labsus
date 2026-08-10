# -*- coding: utf-8 -*-
"""
======================================================================
  HEALTHCARE NETWORK FRAGMENTATION INDEX (HNFI)
======================================================================
Objetivo: quantificar o quanto a rede assistencial usada pelos
residentes de um município está fragmentada entre muitos
estabelecimentos/municípios de destino diferentes, em vez de
concentrada num único provedor de referência.

Hipótese: redes mais fragmentadas têm menor continuidade assistencial.

Reaproveita os carregadores de fluxo SIH/SIA já escritos em hae.py
(mesma exceção documentada lá: não há ainda um indicador de fluxo em
src/features/, então o dado bruto é tocado aqui, não em features/).

Métricas por município de residência:
  - N_ESTABELECIMENTOS_DISTINTOS_HNFI: nº de códigos CNES distintos
    usados pelos residentes nas internações (SIH) — o "hospital" do
    enunciado original.
  - SHANNON_DIVERSIDADE_HOSPITAIS_HNFI: diversidade de Shannon sobre a
    distribuição de internações entre esses estabelecimentos.
  - RIQUEZA_DESTINOS_HNFI: nº de municípios de atendimento distintos
    (SIH+SIA combinados).

Simplificação assumida: a "modularidade" do enunciado original (medida
de grafos que exigiria detecção de comunidades, ex.: Louvain) fica de
fora desta primeira versão — as três métricas acima já capturam
fragmentação de forma direta e auditável, sem a dependência extra e a
complexidade de validação de um algoritmo de grafos.

HNFI = combinar_indice_composto() das três métricas — quanto maior,
mais fragmentada a rede usada pelo município.
"""
import pandas as pd

from .hae import carregar_internacoes, carregar_producao_ambulatorial
from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import calcular_diversidade, combinar_indice_composto


def _metricas_fragmentacao(df_sih: pd.DataFrame, df_sia: pd.DataFrame) -> pd.DataFrame:
    linhas = {}

    if not df_sih.empty and {'MUNIC_RES', 'CNES', 'MUNIC_MOV'}.issubset(df_sih.columns):
        df_sih = df_sih.copy()
        df_sih['MUNIC_RES'] = df_sih['MUNIC_RES'].astype(str).str[:6]
        for municipio, grupo in df_sih.groupby('MUNIC_RES'):
            n_estabelecimentos = grupo['CNES'].nunique()
            diversidade = calcular_diversidade(grupo['CNES'].value_counts())
            destinos_sih = set(grupo['MUNIC_MOV'].astype(str).str[:6].unique())
            linhas.setdefault(municipio, {'destinos': set()})
            linhas[municipio]['N_ESTABELECIMENTOS_DISTINTOS_HNFI'] = n_estabelecimentos
            linhas[municipio]['SHANNON_DIVERSIDADE_HOSPITAIS_HNFI'] = diversidade['shannon']
            linhas[municipio]['destinos'] |= destinos_sih

    if not df_sia.empty and {'PA_MUNPCN', 'PA_UFMUN'}.issubset(df_sia.columns):
        df_sia = df_sia.copy()
        df_sia['PA_MUNPCN'] = df_sia['PA_MUNPCN'].astype(str).str[:6]
        for municipio, grupo in df_sia.groupby('PA_MUNPCN'):
            destinos_sia = set(grupo['PA_UFMUN'].astype(str).str[:6].unique())
            linhas.setdefault(municipio, {'destinos': set()})
            linhas[municipio].setdefault('N_ESTABELECIMENTOS_DISTINTOS_HNFI', 0)
            linhas[municipio].setdefault('SHANNON_DIVERSIDADE_HOSPITAIS_HNFI', 0.0)
            linhas[municipio]['destinos'] |= destinos_sia

    registros = []
    for municipio, valores in linhas.items():
        registros.append({
            'cod_mun_ibge_6': municipio,
            'N_ESTABELECIMENTOS_DISTINTOS_HNFI': valores.get('N_ESTABELECIMENTOS_DISTINTOS_HNFI', 0),
            'SHANNON_DIVERSIDADE_HOSPITAIS_HNFI': valores.get('SHANNON_DIVERSIDADE_HOSPITAIS_HNFI', 0.0),
            'RIQUEZA_DESTINOS_HNFI': len(valores.get('destinos', set())),
        })
    if not registros:
        return pd.DataFrame(columns=['N_ESTABELECIMENTOS_DISTINTOS_HNFI', 'SHANNON_DIVERSIDADE_HOSPITAIS_HNFI', 'RIQUEZA_DESTINOS_HNFI'])
    return pd.DataFrame(registros).set_index('cod_mun_ibge_6')


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando HNFI: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = carregar_internacoes(uf, ano)
            df_sia = carregar_producao_ambulatorial(uf, ano)
            metricas = _metricas_fragmentacao(df_sih, df_sia)

            df = df_base.join(metricas, how='left')
            colunas = ['N_ESTABELECIMENTOS_DISTINTOS_HNFI', 'SHANNON_DIVERSIDADE_HOSPITAIS_HNFI', 'RIQUEZA_DESTINOS_HNFI']
            df[colunas] = df[colunas].fillna(0)

            df['HNFI'] = combinar_indice_composto(df, colunas)

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de HNFI foi processado.")
        return pd.DataFrame()

    print("✅ HNFI processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Healthcare Network Fragmentation Index (HNFI) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "hnfi.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
