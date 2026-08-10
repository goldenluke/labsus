# -*- coding: utf-8 -*-
"""
======================================================================
  TERRITORIAL EPIDEMIOLOGICAL RESILIENCE INDEX (TERI)
======================================================================
Objetivo: mensurar a capacidade de um território retornar ao seu
patamar basal depois de um aumento de incidência/utilização —
resiliência entendida como velocidade de recuperação, não apenas
ausência de choque.

Requer uma série de VÁRIOS anos por município (recomenda-se --anos com
pelo menos 5-6 anos), assim como o PHSI.

Indicadores usados, um valor por ano (src/features/):
  - complexidade_hospitalar.N_INTERNACOES_HOSP (SIH)
  - mortalidade_geral.TAXA_MORTALIDADE_GERAL (SIM)

(Mesma decisão do PHSI: SINAN/incidência fica de fora por não ter uma
métrica única sem escolher um agravo específico — CNES/capacidade
instalada também não entra diretamente na série temporal aqui, mas
pondera o resultado final via capacidade_assistencial.)

Método (src/utils/indices_compostos.metricas_pico_recuperacao — proxy
estrutural, sem ajuste de modelo): localiza o ano de pico de cada série
e mede quantos anos depois ela volta a ficar perto do valor do primeiro
ano (baseline) — tempo até pico, tempo até recuperação, velocidade de
recuperação (queda por ano entre pico e recuperação). Município que
nunca recupera dentro da janela de anos processada fica com
tempo_ate_recuperacao em branco (NaN) — não é um erro, é a maior janela
possível com os anos informados.

TERI = combinar_indice_composto() da capacidade instalada
(capacidade_assistencial.IND_CAPACIDADE_ASSISTENCIAL, o "colchão" que
amortece o choque) com a velocidade de recuperação das duas séries
(internações e mortalidade) — quanto maior a capacidade E mais rápida
a recuperação, maior o TERI.
"""
import pandas as pd

from ..features import complexidade_hospitalar, mortalidade_geral, capacidade_assistencial
from ..utils.indices_compostos import metricas_pico_recuperacao, combinar_indice_composto


def _series_por_municipio(uf: str, anos: list, arquivo_populacao) -> dict:
    series = {}
    for ano in sorted(anos):
        df_hosp = complexidade_hospitalar.processar_dados(ufs=[uf], anos=[ano], arquivo_populacao=arquivo_populacao)
        df_mort = mortalidade_geral.processar_dados(ufs=[uf], anos=[ano], arquivo_populacao=arquivo_populacao)
        if df_hosp.empty:
            continue
        for _, row in df_hosp.iterrows():
            municipio = row['cod_mun_ibge_6']
            series.setdefault(municipio, {'internacoes': {}, 'mortalidade': {}, 'nome': row.get('municipio'), 'populacao': row.get('populacao')})
            series[municipio]['internacoes'][ano] = row.get('N_INTERNACOES_HOSP', 0)
        if not df_mort.empty:
            for _, row in df_mort.iterrows():
                municipio = row['cod_mun_ibge_6']
                series.setdefault(municipio, {'internacoes': {}, 'mortalidade': {}, 'nome': row.get('municipio'), 'populacao': row.get('populacao')})
                series[municipio]['mortalidade'][ano] = row.get('TAXA_MORTALIDADE_GERAL', 0)
    return series


def processar_dados(ufs, anos, arquivo_populacao, meses=None, **kwargs):
    anos = anos if isinstance(anos, list) else [anos]
    if len(anos) < 4:
        print("⚠️ TERI precisa de vários anos para detectar pico/recuperação (recomenda-se >= 5). Prosseguindo mesmo assim com menos precisão.")

    df_cap = capacidade_assistencial.processar_dados(ufs=ufs, anos=[max(anos)], arquivo_populacao=arquivo_populacao)
    mapa_capacidade = df_cap.set_index('cod_mun_ibge_6')['IND_CAPACIDADE_ASSISTENCIAL'].to_dict() if not df_cap.empty else {}

    linhas = []
    for uf in ufs:
        print(f"\n=== Processando TERI: {uf}/{anos} ===")
        series_municipio = _series_por_municipio(uf, anos, arquivo_populacao)

        for municipio, dados in series_municipio.items():
            serie_internacoes = pd.Series(dados['internacoes']).sort_index()
            serie_mortalidade = pd.Series(dados['mortalidade']).sort_index()

            r_internacoes = metricas_pico_recuperacao(serie_internacoes)
            r_mortalidade = metricas_pico_recuperacao(serie_mortalidade)

            linhas.append({
                'cod_mun_ibge_6': municipio, 'UF': uf, 'ANO': max(anos),
                'municipio': dados.get('nome'), 'populacao': dados.get('populacao'),
                'TEMPO_ATE_PICO_INTERNACOES_TERI': r_internacoes['tempo_ate_pico'],
                'TEMPO_ATE_RECUPERACAO_INTERNACOES_TERI': r_internacoes['tempo_ate_recuperacao'],
                'VELOCIDADE_RECUPERACAO_INTERNACOES_TERI': r_internacoes['velocidade_recuperacao'],
                'TEMPO_ATE_PICO_MORTALIDADE_TERI': r_mortalidade['tempo_ate_pico'],
                'TEMPO_ATE_RECUPERACAO_MORTALIDADE_TERI': r_mortalidade['tempo_ate_recuperacao'],
                'VELOCIDADE_RECUPERACAO_MORTALIDADE_TERI': r_mortalidade['velocidade_recuperacao'],
                'IND_CAPACIDADE_ASSISTENCIAL_TERI': mapa_capacidade.get(municipio, 0),
            })

    if not linhas:
        print("\n⚠️ Nenhum dado de TERI foi processado.")
        return pd.DataFrame()

    df = pd.DataFrame(linhas)
    # tempo_ate_recuperacao pode ser NaN (nunca recuperou na janela) — trata
    # como "recuperação lenta" (pior caso observável) em vez de excluir a
    # linha, para não perder o município do índice final.
    colunas_velocidade = ['VELOCIDADE_RECUPERACAO_INTERNACOES_TERI', 'VELOCIDADE_RECUPERACAO_MORTALIDADE_TERI']
    df[colunas_velocidade] = df[colunas_velocidade].fillna(0).abs()

    df['TERI'] = combinar_indice_composto(
        df, ['IND_CAPACIDADE_ASSISTENCIAL_TERI'] + colunas_velocidade
    )

    print("✅ TERI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Territorial Epidemiological Resilience Index (TERI) por município, sobre uma série de anos.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2017, 2018, 2019, 2020, 2021, 2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "teri.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
