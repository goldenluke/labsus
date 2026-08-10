# -*- coding: utf-8 -*-
"""
======================================================================
  DETECÇÃO DE QUEBRA ESTRUTURAL (TESTE DE CHOW) EM SÉRIE DE ÓBITOS
======================================================================
Este script varre uma série anual (ou mensal) de óbitos por uma causa
configurável (prefixo de CID-10) em busca do ponto no tempo em que a
TENDÊNCIA da série mudou de forma estatisticamente significante — por
exemplo, o início de uma epidemia, o efeito de uma nova política pública,
ou uma mudança na codificação/qualidade do dado.

Método: Teste de Chow, o clássico teste estatístico de quebra estrutural
em regressão — para cada ano candidato, compara o ajuste de UMA regressão
linear sobre a série inteira contra o ajuste de DUAS regressões separadas
(antes/depois do candidato); se o ganho de ajuste ao "quebrar" a série for
grande demais para ser explicado por acaso (teste F), o ano é uma quebra
estrutural candidata. O script reporta o ano com maior evidência.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as scipy_stats

from pysus.online_data.SIM import download as download_sim


def carregar_serie_obitos(uf: str, anos: list, cid_prefixos: list) -> pd.Series:
    contagens = {}
    for ano in sorted(anos):
        print(f"[LOG] Baixando SIM para {uf}/{ano}...")
        try:
            downloaded = download_sim(states=uf, years=ano, groups=['CID10'])
            if isinstance(downloaded, list):
                if not downloaded:
                    print(f"  -> Nenhum dado disponível para {ano} (ainda não publicado).")
                    continue
                df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True)
            else:
                df = downloaded.to_dataframe()
        except Exception as e:
            print(f"  -> ❌ Falha ao baixar {ano}: {e}")
            continue
        df_causa = df[df['CAUSABAS'].astype(str).str.startswith(tuple(cid_prefixos))]
        contagens[ano] = len(df_causa)

    if not contagens:
        raise ValueError("Nenhum dado de óbito pôde ser carregado para os anos informados.")
    serie = pd.Series(contagens).sort_index()
    return serie


def teste_chow(serie: pd.Series, ano_candidato: int):
    """Compara o ajuste de uma regressão linear única vs. duas regressões
    separadas antes/depois de `ano_candidato`. Retorna a estatística F e o p-valor."""
    x = np.arange(len(serie))
    y = serie.values.astype(float)
    idx_quebra = serie.index.get_loc(ano_candidato)

    if idx_quebra < 2 or (len(serie) - idx_quebra) < 2:
        return None, None  # poucos pontos de cada lado para ajustar uma reta

    X_completo = sm.add_constant(x)
    modelo_completo = sm.OLS(y, X_completo).fit()
    rss_completo = np.sum(modelo_completo.resid ** 2)

    X1 = sm.add_constant(x[:idx_quebra])
    modelo1 = sm.OLS(y[:idx_quebra], X1).fit()
    X2 = sm.add_constant(x[idx_quebra:])
    modelo2 = sm.OLS(y[idx_quebra:], X2).fit()
    rss_separado = np.sum(modelo1.resid ** 2) + np.sum(modelo2.resid ** 2)

    k = 2  # nº de parâmetros por regressão (intercepto + inclinação)
    n = len(y)
    numerador = (rss_completo - rss_separado) / k
    denominador = rss_separado / (n - 2 * k)
    if denominador <= 0:
        return None, None
    f_stat = numerador / denominador
    p_valor = 1 - scipy_stats.f.cdf(f_stat, k, n - 2 * k)
    return f_stat, p_valor


def escanear_quebras(serie: pd.Series, margem_minima: int = 3) -> pd.DataFrame:
    resultados = []
    anos_candidatos = serie.index[margem_minima:-margem_minima] if len(serie) > 2 * margem_minima else serie.index[1:-1]
    for ano in anos_candidatos:
        f_stat, p_valor = teste_chow(serie, ano)
        if f_stat is not None:
            resultados.append({'ANO_CANDIDATO': ano, 'F_ESTATISTICA': f_stat, 'P_VALOR': p_valor})
    return pd.DataFrame(resultados).sort_values('F_ESTATISTICA', ascending=False)


def gerar_grafico(serie: pd.Series, ano_quebra, cid_nome: str, uf: str, dir_saida: Path):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(11, 6))
    plt.plot(serie.index, serie.values, marker='o', color='black')
    if ano_quebra is not None:
        plt.axvline(ano_quebra, color='red', linestyle='--', label=f'Quebra estrutural estimada ({ano_quebra})')
        plt.legend()
    plt.title(f"Série de Óbitos por '{cid_nome}' em {uf} — Detecção de Quebra Estrutural")
    plt.xlabel('Ano')
    plt.ylabel('Nº de óbitos')
    caminho_fig = dir_saida / f"quebra_estrutural_{cid_nome.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    cid_nome = "-".join(args.cids)

    print(f"\n--- [ETAPA 1] Carregando série anual de óbitos por '{cid_nome}' em {args.uf} ---")
    serie = carregar_serie_obitos(args.uf, args.anos, args.cids)
    print(f"✅ Série com {len(serie)} anos.")
    print(serie.to_string())

    if len(serie) < 7:
        print("❌ Série muito curta para um teste de quebra estrutural confiável (mínimo recomendado: 7 anos).")
        return

    print(f"\n--- [ETAPA 2] Escaneando anos candidatos a quebra estrutural (Teste de Chow) ---")
    df_resultados = escanear_quebras(serie)

    if df_resultados.empty:
        print("⚠️ Não foi possível calcular o teste em nenhum ano candidato (série curta demais).")
        return

    melhor = df_resultados.iloc[0]
    ano_quebra = melhor['ANO_CANDIDATO'] if melhor['P_VALOR'] < args.significancia else None

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: QUEBRA ESTRUTURAL NA SÉRIE DE ÓBITOS POR '{cid_nome}' EM {args.uf} ---")
    print("=" * 70)
    print(df_resultados.to_string(index=False))
    print("-" * 70)
    if ano_quebra is not None:
        print(f"✅ Quebra estrutural estatisticamente significante detectada em {int(ano_quebra)} (F={melhor['F_ESTATISTICA']:.2f}, p={melhor['P_VALOR']:.4f}).")
    else:
        print(f"⚠️ Nenhuma quebra estrutural estatisticamente significante (melhor candidato: {int(melhor['ANO_CANDIDATO'])}, p={melhor['P_VALOR']:.4f}).")
    print("=" * 70)

    caminho_csv = dir_saida / f"teste_chow_{cid_nome.lower()}_{args.uf.lower()}.csv"
    df_resultados.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resultados completos salvos em: '{caminho_csv}'")

    gerar_grafico(serie, ano_quebra, cid_nome, args.uf, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 DETECÇÃO DE QUEBRA ESTRUTURAL CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecta quebras estruturais (Teste de Chow) em uma série anual de óbitos.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos a incluir na série (recomenda-se >= 8 anos).")
    parser.add_argument("--cids", nargs="+", default=['I2'], help="Prefixos de CID-10 da causa de óbito (ex: I2 para doenças isquêmicas do coração).")
    parser.add_argument("--significancia", type=float, default=0.05, help="Limiar de p-valor para considerar a quebra significante.")
    parser.add_argument("--dir_saida", type=str, default="outputs/quebra_estrutural_obitos", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
