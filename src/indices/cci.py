# -*- coding: utf-8 -*-
"""
======================================================================
  CONTINUITY OF CARE INDEX (CCI) — PROXY AGREGADO, SEM LINKAGE
======================================================================
Objetivo: medir a continuidade do cuidado (uso do ambulatório para
resolver antes de precisar de internação, e desfecho favorável quando
a internação acontece).

Problema (reconhecido no enunciado original): a definição clássica de
continuidade — consultas antes da internação, retorno após a alta,
mortalidade após internação POR PACIENTE — exige linkage individual
entre SIA/SIH/SIM, que este projeto evita por desenho. Este módulo
implementa a alternativa sugerida: uma estimativa em nível agregado
(por município), sem linkage.

Indicadores/dados usados:
  - Volume de produção ambulatorial (SIA/PA, carregado via
    hae.carregar_producao_ambulatorial) por município de residência.
  - complexidade_hospitalar.N_INTERNACOES_HOSP (SIH) — volume de
    internações do município.
  - resolutividade_hospitalar.IND_RESOLUTIVIDADE (SIH) — proxy de
    desfecho favorável quando a internação ocorre.

Métrica: RAZAO_AMBULATORIAL_HOSPITALAR = procedimentos SIA / (internações
SIH + 1) — municípios que resolvem mais na atenção ambulatorial antes de
precisar de internação tendem a ter essa razão mais alta. CCI combina
essa razão com a resolutividade hospitalar (combinar_indice_composto).
Não captura o retorno pós-alta nem o desfecho por paciente — é um proxy
estrutural, não uma medida de continuidade individual.
"""
import pandas as pd

from .hae import carregar_producao_ambulatorial
from ..features import complexidade_hospitalar, resolutividade_hospitalar
from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import combinar_indice_composto

CHAVES = ['cod_mun_ibge_6', 'ANO', 'UF']


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    print("\n=== Calculando CCI: chamando indicadores hospitalares + volume ambulatorial (SIA) ===")

    df_hosp = complexidade_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    df_resol = resolutividade_hospitalar.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)

    if df_hosp.empty:
        print("⚠️ Nenhum dado disponível para calcular o CCI.")
        return pd.DataFrame()

    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"  -> Carregando volume ambulatorial (SIA) para {uf}/{ano}...")
            df_sia = carregar_producao_ambulatorial(uf, ano)
            if df_sia.empty or 'PA_MUNPCN' not in df_sia.columns:
                n_ambulatorial = pd.Series(dtype=float, name='N_PROCEDIMENTOS_AMBULATORIAIS_CCI')
            else:
                n_ambulatorial = df_sia['PA_MUNPCN'].astype(str).str[:6].value_counts().rename('N_PROCEDIMENTOS_AMBULATORIAIS_CCI')
                n_ambulatorial.index.name = 'cod_mun_ibge_6'

            df_periodo = df_hosp[(df_hosp['UF'] == uf) & (df_hosp['ANO'] == ano)].set_index('cod_mun_ibge_6')
            df_periodo = df_periodo.join(n_ambulatorial, how='left')
            df_periodo['N_PROCEDIMENTOS_AMBULATORIAIS_CCI'] = df_periodo['N_PROCEDIMENTOS_AMBULATORIAIS_CCI'].fillna(0)
            resultados.append(df_periodo.reset_index())

    df = pd.concat(resultados, ignore_index=True)
    df = df[CHAVES + ['municipio', 'populacao', 'N_INTERNACOES_HOSP', 'N_PROCEDIMENTOS_AMBULATORIAIS_CCI']]
    df = df.merge(df_resol[CHAVES + ['IND_RESOLUTIVIDADE']], on=CHAVES, how='left')
    df['IND_RESOLUTIVIDADE'] = df['IND_RESOLUTIVIDADE'].fillna(0)

    df['RAZAO_AMBULATORIAL_HOSPITALAR_CCI'] = df['N_PROCEDIMENTOS_AMBULATORIAIS_CCI'] / (df['N_INTERNACOES_HOSP'] + 1)

    df['CCI'] = combinar_indice_composto(df, ['RAZAO_AMBULATORIAL_HOSPITALAR_CCI', 'IND_RESOLUTIVIDADE'])

    # N_INTERNACOES_HOSP e IND_RESOLUTIVIDADE já são nomes de indicadores de
    # 1ª camada (complexidade_hospitalar.py, resolutividade_hospitalar.py) —
    # se o usuário selecionar as duas camadas na mesma integração, colidiriam
    # com as colunas deste índice. Renomeia com o sufixo _CCI.
    df = df.rename(columns={'N_INTERNACOES_HOSP': 'N_INTERNACOES_HOSP_CCI', 'IND_RESOLUTIVIDADE': 'IND_RESOLUTIVIDADE_CCI'})

    print("✅ CCI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Continuity of Care Index (CCI, proxy agregado sem linkage) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "cci.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
