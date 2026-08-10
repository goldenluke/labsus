# -*- coding: utf-8 -*-
"""
======================================================================
  POPULATION HEALTH STABILITY INDEX (PHSI)
======================================================================
Objetivo: mensurar a estabilidade dinâmica da saúde populacional de um
município ao longo do tempo — conversa diretamente com a literatura de
sistemas complexos e "critical slowing down" (sinais precoces de
transição crítica: a série fica mais lenta para voltar ao equilíbrio
antes de uma mudança de regime).

Requer uma série de VÁRIOS anos por município (recomenda-se --anos com
pelo menos 5-6 anos) — diferente dos demais índices desta leva, que
operam sobre um único ano por vez.

Indicadores usados, um valor por ano (src/features/):
  - complexidade_hospitalar.N_INTERNACOES_HOSP (SIH, proxy de utilização)
  - mortalidade_geral.TAXA_MORTALIDADE_GERAL (SIM)

(SINAN não entra: "incidência" não é uma métrica única sem escolher um
agravo específico, e este índice foi desenhado para ser agnóstico a
agravo — outra forma de manter a promessa de não exigir uma escolha
metodológica arbitrária.)

Métricas por série (src/utils/indices_compostos.metricas_estabilidade_serie):
variância, autocorrelação lag-1, skewness, kurtosis, coeficiente de
variação — calculadas separadamente para a série de internações e a de
mortalidade, depois combinadas.

PHSI = 100 - combinar_indice_composto(variância/CV/|autocorrelação lag-1|
normalizados) — quanto MAIOR o PHSI, mais ESTÁVEL a série (a inversão é
proposital: intuitivamente, "estabilidade" deveria crescer com o índice).
"""
import pandas as pd

from ..features import complexidade_hospitalar, mortalidade_geral
from ..utils.indices_compostos import metricas_estabilidade_serie, combinar_indice_composto


def _series_por_municipio(uf: str, anos: list, arquivo_populacao) -> dict:
    """Retorna {cod_mun_ibge_6: {'internacoes': pd.Series(index=ano), 'mortalidade': pd.Series(index=ano)}}."""
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
        print("⚠️ PHSI precisa de vários anos para calcular estabilidade dinâmica (recomenda-se >= 5). Prosseguindo mesmo assim com menos precisão.")

    linhas = []
    for uf in ufs:
        print(f"\n=== Processando PHSI: {uf}/{anos} ===")
        series_municipio = _series_por_municipio(uf, anos, arquivo_populacao)

        for municipio, dados in series_municipio.items():
            serie_internacoes = pd.Series(dados['internacoes']).sort_index()
            serie_mortalidade = pd.Series(dados['mortalidade']).sort_index()

            m_internacoes = metricas_estabilidade_serie(serie_internacoes)
            m_mortalidade = metricas_estabilidade_serie(serie_mortalidade)

            linhas.append({
                'cod_mun_ibge_6': municipio, 'UF': uf, 'ANO': max(anos),
                'municipio': dados.get('nome'), 'populacao': dados.get('populacao'),
                'VARIANCIA_INTERNACOES_PHSI': m_internacoes['variancia'],
                'AUTOCORR_LAG1_INTERNACOES_PHSI': abs(m_internacoes['autocorrelacao_lag1']),
                'CV_INTERNACOES_PHSI': abs(m_internacoes['coef_variacao']),
                'VARIANCIA_MORTALIDADE_PHSI': m_mortalidade['variancia'],
                'AUTOCORR_LAG1_MORTALIDADE_PHSI': abs(m_mortalidade['autocorrelacao_lag1']),
                'CV_MORTALIDADE_PHSI': abs(m_mortalidade['coef_variacao']),
            })

    if not linhas:
        print("\n⚠️ Nenhum dado de PHSI foi processado.")
        return pd.DataFrame()

    df = pd.DataFrame(linhas)
    colunas_instabilidade = [
        'VARIANCIA_INTERNACOES_PHSI', 'AUTOCORR_LAG1_INTERNACOES_PHSI', 'CV_INTERNACOES_PHSI',
        'VARIANCIA_MORTALIDADE_PHSI', 'AUTOCORR_LAG1_MORTALIDADE_PHSI', 'CV_MORTALIDADE_PHSI',
    ]
    df[colunas_instabilidade] = df[colunas_instabilidade].fillna(0)
    df['PHSI'] = 100 - combinar_indice_composto(df, colunas_instabilidade)

    print("✅ PHSI processado com sucesso.")
    return df


if __name__ == '__main__':
    import argparse
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description="Calcula o Population Health Stability Index (PHSI) por município, sobre uma série de anos.")
    parser.add_argument("--ufs", nargs="+", default=["TO"])
    parser.add_argument("--anos", nargs="+", type=int, default=[2017, 2018, 2019, 2020, 2021, 2022])
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"))
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)
    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "phsi.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida}'")
