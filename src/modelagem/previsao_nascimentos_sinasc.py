# -*- coding: utf-8 -*-
"""
======================================================================
  PREVISÃO DE NASCIMENTOS (SINASC) — PROPHET
======================================================================
Mesma lógica de `previsao_internacoes` (SIH), mas para nascidos vivos do
SINASC: agrega a série histórica MENSAL de nascimentos e ajusta um
modelo Prophet para projetar os próximos meses com intervalo de
incerteza — insumo direto para planejamento de leitos obstétricos/
neonatais e dimensionamento de equipe de maternidade com antecedência,
em vez de reagir à demanda já realizada.
"""

import argparse
from pathlib import Path

import pandas as pd

from pysus.online_data.SINASC import download as download_sinasc

from src.utils.series_temporais import prever_serie_mensal_prophet, gerar_grafico_previsao_prophet


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_nascimentos(ufs: list, anos: list) -> pd.DataFrame:
    dfs = []
    for uf in ufs:
        for ano in anos:
            print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
            try:
                downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
            except Exception as e:
                print(f"  -> ❌ Falha ao baixar {uf}/{ano}: {e}")
                continue
            arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
            if not arquivos:
                print(f"  -> ⚠️ Nenhum dado disponível para {uf}/{ano} (ainda não publicado).")
                continue
            dfs.append(pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True))
    if not dfs:
        raise FileNotFoundError("Nenhum dado do SINASC pôde ser carregado para as UFs/anos informados.")
    return pd.concat(dfs, ignore_index=True)


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    ufs = [u.upper() for u in (args.ufs if isinstance(args.ufs, list) else [args.ufs])]
    anos_historico = args.anos_historico if isinstance(args.anos_historico, list) else [args.anos_historico]

    print(f"\n--- [ETAPA 1] Carregando nascimentos (SINASC) para {ufs}/{anos_historico} ---")
    df = carregar_nascimentos(ufs, anos_historico)
    print(f"✅ {len(df)} nascimentos carregados.")

    df['DTNASC'] = pd.to_datetime(df['DTNASC'], format='%d%m%Y', errors='coerce')
    df = df.dropna(subset=['DTNASC'])

    serie = df.resample('MS', on='DTNASC').size()
    serie = serie.asfreq('MS', fill_value=0)
    print(f"✅ Série mensal com {len(serie)} meses, {serie.sum()} nascimentos totais.")

    if len(serie) < 12:
        print("❌ Série muito curta para uma previsão confiável (mínimo recomendado: 12 meses). Amplie --anos-historico.")
        return

    print(f"\n--- [ETAPA 2] Ajustando Prophet e prevendo {args.meses_futuros} meses ---")
    df_previsao = prever_serie_mensal_prophet(serie, args.meses_futuros)

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: PREVISÃO DE NASCIMENTOS EM {ufs} ---")
    print("=" * 70)
    print(df_previsao.tail(args.meses_futuros + 3).round(1).to_string(index=False))
    print("=" * 70)

    ufs_str = '-'.join(ufs).lower()
    caminho_csv = dir_saida / f"previsao_nascimentos_{ufs_str}.csv"
    df_previsao.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Previsão salva em: '{caminho_csv}'")

    titulo = f"Previsão de Nascimentos (Prophet) — {', '.join(ufs)}"
    caminho_fig = dir_saida / f"previsao_nascimentos_{ufs_str}.png"
    gerar_grafico_previsao_prophet(df_previsao, titulo, caminho_fig)
    print(f"📈 Gráfico salvo em: '{caminho_fig}'")

    print("\n" + "=" * 80)
    print("🎉 PREVISÃO DE NASCIMENTOS CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prevê a série mensal de nascimentos (SINASC) com Prophet.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos-historico", dest="anos_historico", nargs="+", type=int, required=True, help="Anos de dados históricos (recomenda-se >= 2 anos).")
    parser.add_argument("--meses-futuros", dest="meses_futuros", type=int, default=6, help="Nº de meses a prever no futuro.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsao_nascimentos", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
