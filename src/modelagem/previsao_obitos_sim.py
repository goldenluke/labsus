# -*- coding: utf-8 -*-
"""
======================================================================
  PREVISÃO DE ÓBITOS (SIM) — PROPHET
======================================================================
Mesma lógica de `previsao_internacoes` (SIH), mas para óbitos do SIM:
agrega a série histórica MENSAL de óbitos (opcionalmente filtrada por
prefixo(s) de CID-10 da causa básica) e ajusta um modelo Prophet para
projetar os próximos meses com intervalo de incerteza — útil para
antecipar pressão sobre serviços funerários/necrotérios, campanhas de
prevenção sazonais (ex.: doenças respiratórias no inverno) e para
comparar contra "Excesso de Mortalidade" (que mede desvio do passado,
não projeta o futuro).
"""

import argparse
from pathlib import Path

import pandas as pd

from pysus.online_data.SIM import download as download_sim

from src.utils.series_temporais import prever_serie_mensal_prophet, gerar_grafico_previsao_prophet


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_obitos(ufs: list, anos: list, cid_prefixos: list) -> pd.DataFrame:
    dfs = []
    for uf in ufs:
        for ano in anos:
            print(f"[LOG] Baixando SIM/CID10 para {uf}/{ano}...")
            try:
                downloaded = download_sim(states=uf, years=ano, groups=['CID10'])
            except Exception as e:
                print(f"  -> ❌ Falha ao baixar {uf}/{ano}: {e}")
                continue
            arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
            if not arquivos:
                print(f"  -> ⚠️ Nenhum dado disponível para {uf}/{ano} (ainda não publicado).")
                continue
            dfs.append(pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True))
    if not dfs:
        raise FileNotFoundError("Nenhum dado do SIM pôde ser carregado para as UFs/anos informados.")
    df = pd.concat(dfs, ignore_index=True)

    if cid_prefixos:
        df['CAUSABAS'] = df['CAUSABAS'].astype(str)
        df = df[df['CAUSABAS'].str.startswith(tuple(cid_prefixos))].copy()
    return df


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    ufs = [u.upper() for u in (args.ufs if isinstance(args.ufs, list) else [args.ufs])]
    anos_historico = args.anos_historico if isinstance(args.anos_historico, list) else [args.anos_historico]
    cid_prefixos = args.cid_prefixos if isinstance(args.cid_prefixos, list) else ([args.cid_prefixos] if args.cid_prefixos else [])

    print(f"\n--- [ETAPA 1] Carregando óbitos (SIM) para {ufs}/{anos_historico} ---")
    df = carregar_obitos(ufs, anos_historico, cid_prefixos)
    print(f"✅ {len(df)} óbitos carregados" + (f" (CID-10 iniciando em {cid_prefixos})" if cid_prefixos else " (todas as causas)") + ".")

    df['DTOBITO'] = pd.to_datetime(df['DTOBITO'], format='%d%m%Y', errors='coerce')
    df = df.dropna(subset=['DTOBITO'])

    serie = df.resample('MS', on='DTOBITO').size()
    serie = serie.asfreq('MS', fill_value=0)
    print(f"✅ Série mensal com {len(serie)} meses, {serie.sum()} óbitos totais.")

    if len(serie) < 12:
        print("❌ Série muito curta para uma previsão confiável (mínimo recomendado: 12 meses). Amplie --anos-historico.")
        return

    print(f"\n--- [ETAPA 2] Ajustando Prophet e prevendo {args.meses_futuros} meses ---")
    df_previsao = prever_serie_mensal_prophet(serie, args.meses_futuros)

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: PREVISÃO DE ÓBITOS EM {ufs} ---")
    print("=" * 70)
    print(df_previsao.tail(args.meses_futuros + 3).round(1).to_string(index=False))
    print("=" * 70)

    cids_str = '-'.join(cid_prefixos) if cid_prefixos else 'todas-causas'
    ufs_str = '-'.join(ufs).lower()
    caminho_csv = dir_saida / f"previsao_obitos_{cids_str.lower()}_{ufs_str}.csv"
    df_previsao.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Previsão salva em: '{caminho_csv}'")

    titulo = f"Previsão de Óbitos (Prophet) — {', '.join(ufs)}" + (f" (CID: {', '.join(cid_prefixos)})" if cid_prefixos else "")
    caminho_fig = dir_saida / f"previsao_obitos_{cids_str.lower()}_{ufs_str}.png"
    gerar_grafico_previsao_prophet(df_previsao, titulo, caminho_fig)
    print(f"📈 Gráfico salvo em: '{caminho_fig}'")

    print("\n" + "=" * 80)
    print("🎉 PREVISÃO DE ÓBITOS CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prevê a série mensal de óbitos (SIM) com Prophet.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos-historico", dest="anos_historico", nargs="+", type=int, required=True, help="Anos de dados históricos (recomenda-se >= 2 anos).")
    parser.add_argument("--cid-prefixos", dest="cid_prefixos", nargs="+", default=[], help="Prefixos de CID-10 da causa básica (ex: I2 para doenças isquêmicas do coração). Vazio = todas as causas.")
    parser.add_argument("--meses-futuros", dest="meses_futuros", type=int, default=6, help="Nº de meses a prever no futuro.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsao_obitos", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
