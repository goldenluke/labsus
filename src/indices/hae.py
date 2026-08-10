# -*- coding: utf-8 -*-
"""
======================================================================
  HEALTHCARE FLOW ENTROPY (HAE) — sigla mantida por compatibilidade
======================================================================
Objetivo: mensurar a dispersão dos deslocamentos da população de um
município para atendimento — alta entropia = os residentes se atendem
em muitos municípios diferentes; baixa entropia = atendimento
concentrado num único destino (tipicamente o próprio município ou um
polo único).

Nome revisado (era "Healthcare Accessibility Entropy"): o índice não
mede ACESSO — dois municípios podem ter a mesma entropia com realidades
opostas (um com rede bem regionalizada e referência clara para 2 polos,
outro com peregrinação do paciente entre 5 destinos por falta de
resolutividade local). O que ele mede, de fato, é o quão distribuído /
fragmentado é o fluxo assistencial efetivamente usado pelos residentes —
um indicador de centralização/descentralização e regionalização da rede,
não de acessibilidade em si. A sigla HAE é mantida (coluna de saída,
FileType do Django, chave no frontend) para não quebrar integrações já
existentes, mas o nome de exibição passa a ser "Healthcare Flow Entropy".

Nenhum indicador de src/features/ ainda expõe a tabela de fluxo
"município de residência → município de atendimento" (os módulos de
fluxo existentes — analise_fluxo_pacientes.py, fluxo_partos_sinasc.py
etc. — ficam em src/modelagem/, uma camada de resultado analítico, não
de indicador atômico reutilizável). Este módulo carrega o fluxo
diretamente do SIH e do SIA — a única exceção à regra "índice usa só
indicadores" nesta leva, documentada aqui.

Campos de origem/destino no SIA/PA (validados contra o uso consistente
em fluxo_alta_complexidade_sia.py e hnfi.py): PA_MUNPCN é o município de
RESIDÊNCIA do paciente; PA_UFMUN é o município do ESTABELECIMENTO que
realizou o procedimento (atendimento). PA_CMP é competência (ano/mês), não
um código de município — não deve ser confundido com os dois anteriores.

Métrica: para cada município de RESIDÊNCIA, entropia de Shannon (via
calcular_diversidade, o mesmo helper usado por diversidade_epidemiologica
e diversidade_assistencial) sobre a distribuição de municípios de
ATENDIMENTO visitados pelos seus residentes. SIH e SIA são empilhados
num único fluxo ANTES de calcular a entropia (não duas entropias
separadas depois combinadas por média) — Shannon não é linear, então
fazer H(SIH) e H(SIA) e tirar a média faz uma fonte com poucos eventos
(ex.: 2 mil internações) pesar o mesmo que uma com muitos (ex.: 500 mil
procedimentos ambulatoriais), o que não tem leitura epidemiológica.
"""
import pandas as pd

from pysus.online_data.SIH import download as download_sih
from pysus.online_data.SIA import download as download_sia

from ..utils.dataloaders import filtrar_populacao
from ..utils.indices_compostos import calcular_diversidade

N_EVENTOS_MINIMO_CONFIAVEL = 30


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def _combinar_fluxos(df_sih: pd.DataFrame, df_sia: pd.DataFrame) -> pd.DataFrame:
    """Empilha os eventos de SIH e SIA num único fluxo RESIDENCIA->ATENDIMENTO
    antes de calcular a entropia — ver docstring do módulo para o porquê de
    não calcular Shannon separadamente por fonte e depois tirar a média."""
    partes = []
    if not df_sih.empty and {'MUNIC_RES', 'MUNIC_MOV'}.issubset(df_sih.columns):
        partes.append(df_sih[['MUNIC_RES', 'MUNIC_MOV']].rename(
            columns={'MUNIC_RES': 'RESIDENCIA', 'MUNIC_MOV': 'ATENDIMENTO'}))
    if not df_sia.empty and {'PA_MUNPCN', 'PA_UFMUN'}.issubset(df_sia.columns):
        partes.append(df_sia[['PA_MUNPCN', 'PA_UFMUN']].rename(
            columns={'PA_MUNPCN': 'RESIDENCIA', 'PA_UFMUN': 'ATENDIMENTO'}))

    if not partes:
        return pd.DataFrame(columns=['RESIDENCIA', 'ATENDIMENTO'])

    df_fluxo = pd.concat(partes, ignore_index=True).dropna()
    df_fluxo['RESIDENCIA'] = df_fluxo['RESIDENCIA'].astype(str).str[:6]
    df_fluxo['ATENDIMENTO'] = df_fluxo['ATENDIMENTO'].astype(str).str[:6]
    return df_fluxo


def _metricas_fluxo_por_residencia(df_fluxo: pd.DataFrame) -> pd.DataFrame:
    """Para cada município de residência: entropia de Shannon e Simpson do
    fluxo combinado, riqueza de destinos, nº total de eventos (para filtrar
    municípios com amostra pequena e instável), proporção atendida no
    próprio município (P_LOCAL) e a fração do destino dominante (MAX_PI) —
    dois municípios podem ter a mesma entropia com perfis de rede opostos
    (ex.: 90% local + 10% num polo vs. 0% local + 90% num polo + 10% noutro),
    então esses dois complementos evitam essa ambiguidade."""
    colunas = ['N_EVENTOS_HAE', 'SHANNON_ENTROPIA_ACESSO_HAE', 'SIMPSON_DIVERSIDADE_ACESSO_HAE',
               'RIQUEZA_DESTINOS_HAE', 'P_LOCAL_HAE', 'MAX_PI_HAE']
    if df_fluxo.empty:
        return pd.DataFrame(columns=colunas)

    linhas = []
    for municipio, grupo in df_fluxo.groupby('RESIDENCIA'):
        contagens = grupo['ATENDIMENTO'].value_counts()
        d = calcular_diversidade(contagens)
        proporcoes = contagens / contagens.sum()
        linhas.append({
            'cod_mun_ibge_6': municipio,
            'N_EVENTOS_HAE': int(contagens.sum()),
            'SHANNON_ENTROPIA_ACESSO_HAE': d['shannon'],
            'SIMPSON_DIVERSIDADE_ACESSO_HAE': d['simpson'],
            'RIQUEZA_DESTINOS_HAE': d['riqueza'],
            'P_LOCAL_HAE': float(proporcoes.get(municipio, 0.0)),
            'MAX_PI_HAE': float(proporcoes.max()),
        })
    return pd.DataFrame(linhas).set_index('cod_mun_ibge_6')


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


def carregar_producao_ambulatorial(uf: str, ano: int) -> pd.DataFrame:
    try:
        downloaded = download_sia(states=uf, years=ano, months=list(range(1, 13)), groups=['PA'])
    except Exception as e:
        print(f"❌ Erro ao baixar SIA para {uf}/{ano}: {e}")
        return pd.DataFrame()
    arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando HAE: {uf}/{ano} ===")
            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            df_sih = carregar_internacoes(uf, ano)
            df_sia = carregar_producao_ambulatorial(uf, ano)
            df_fluxo = _combinar_fluxos(df_sih, df_sia)
            metricas = _metricas_fluxo_por_residencia(df_fluxo)

            df = df_base.join(metricas, how='left')
            colunas = ['N_EVENTOS_HAE', 'SHANNON_ENTROPIA_ACESSO_HAE', 'SIMPSON_DIVERSIDADE_ACESSO_HAE',
                       'RIQUEZA_DESTINOS_HAE', 'P_LOCAL_HAE', 'MAX_PI_HAE']
            df[colunas] = df[colunas].fillna(0)

            # Shannon sobre poucos eventos é instável (ex.: 2 internações, 1 por
            # destino, já dá H ~= 0.69 — parece "alta diversidade" vindo de uma
            # amostra de 2 pacientes). Sinaliza em vez de descartar a linha, para
            # que dashboards/análises decidam se filtram.
            df['AMOSTRA_PEQUENA_HAE'] = df['N_EVENTOS_HAE'] < N_EVENTOS_MINIMO_CONFIAVEL

            df['HAE'] = df['SHANNON_ENTROPIA_ACESSO_HAE']

            df['UF'] = uf
            resultados.append(df.reset_index())

    if not resultados:
        print("\n⚠️ Nenhum dado de HAE foi processado.")
        return pd.DataFrame()

    print("✅ HAE processado com sucesso.")
    return pd.concat(resultados, ignore_index=True)


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula a Healthcare Flow Entropy (HAE) por município.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "hae.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
