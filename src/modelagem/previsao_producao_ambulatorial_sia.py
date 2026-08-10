# -*- coding: utf-8 -*-
"""
======================================================================
  PREVISÃO DE PRODUÇÃO AMBULATORIAL (SIA/SIGTAP) — PROPHET
======================================================================
Mesma lógica de `previsao_internacoes` (SIH), mas para procedimentos
AMBULATORIAIS do SIA/PA: agrega o volume mensal de procedimentos
aprovados (opcionalmente filtrado por prefixo(s) de código SIGTAP) e
ajusta um modelo Prophet para projetar os próximos meses — insumo para
planejamento orçamentário e de agenda ambulatorial (ex.: antecipar
picos de demanda por quimioterapia, fisioterapia, exames).

Diferente do SIH/SINASC/SIM (baixados por ano inteiro de uma vez), o
SIA é baixado MÊS A MÊS: cada arquivo de competência já corresponde a
um mês conhecido, então a contagem de procedimentos por mês vem
diretamente do loop de download, sem depender de uma coluna de data
por registro.
"""

import argparse
from pathlib import Path

import pandas as pd

from pysus.online_data.SIA import download as download_sia

from src.utils.series_temporais import prever_serie_mensal_prophet, gerar_grafico_previsao_prophet


def _achatar(x):
    if isinstance(x, list):
        for item in x:
            yield from _achatar(item)
    else:
        yield x


def carregar_producao_mensal(ufs: list, anos: list, proc_prefixos: list) -> pd.Series:
    contagens = {}
    for uf in ufs:
        for ano in anos:
            for mes in range(1, 13):
                competencia = pd.Timestamp(year=ano, month=mes, day=1)
                if competencia > pd.Timestamp.today().normalize().replace(day=1):
                    continue
                print(f"[LOG] Baixando SIA/PA para {uf}/{ano}-{mes:02d}...")
                try:
                    downloaded = download_sia(states=uf, years=ano, months=mes, groups=['PA'])
                except Exception as e:
                    print(f"  -> ❌ Falha ao baixar {uf}/{ano}-{mes:02d}: {e}")
                    continue
                arquivos = [f for f in _achatar(downloaded) if hasattr(f, 'to_dataframe')]
                if not arquivos:
                    continue
                df_mes = pd.concat([f.to_dataframe() for f in arquivos], ignore_index=True)
                if proc_prefixos:
                    df_mes['PA_PROC_ID'] = df_mes['PA_PROC_ID'].astype(str)
                    df_mes = df_mes[df_mes['PA_PROC_ID'].str.startswith(tuple(proc_prefixos))]
                contagens[competencia] = contagens.get(competencia, 0) + len(df_mes)

    if not contagens:
        raise FileNotFoundError("Nenhum dado do SIA pôde ser carregado para as UFs/anos informados.")

    serie = pd.Series(contagens).sort_index()
    serie.index.name = 'ds'
    serie = serie.asfreq('MS', fill_value=0)
    return serie


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)
    ufs = [u.upper() for u in (args.ufs if isinstance(args.ufs, list) else [args.ufs])]
    anos_historico = args.anos_historico if isinstance(args.anos_historico, list) else [args.anos_historico]
    proc_prefixos = args.proc_prefixos if isinstance(args.proc_prefixos, list) else ([args.proc_prefixos] if args.proc_prefixos else [])

    print(f"\n--- [ETAPA 1] Carregando produção ambulatorial (SIA/PA) para {ufs}/{anos_historico} ---")
    serie = carregar_producao_mensal(ufs, anos_historico, proc_prefixos)
    print(f"✅ Série mensal com {len(serie)} meses, {serie.sum()} procedimentos totais" +
          (f" (SIGTAP iniciando em {proc_prefixos})" if proc_prefixos else " (todos os procedimentos)") + ".")

    if len(serie) < 12:
        print("❌ Série muito curta para uma previsão confiável (mínimo recomendado: 12 meses). Amplie --anos-historico.")
        return

    print(f"\n--- [ETAPA 2] Ajustando Prophet e prevendo {args.meses_futuros} meses ---")
    df_previsao = prever_serie_mensal_prophet(serie, args.meses_futuros)

    print("\n" + "=" * 70)
    print(f"--- RESULTADO: PREVISÃO DE PRODUÇÃO AMBULATORIAL EM {ufs} ---")
    print("=" * 70)
    print(df_previsao.tail(args.meses_futuros + 3).round(1).to_string(index=False))
    print("=" * 70)

    procs_str = '-'.join(proc_prefixos) if proc_prefixos else 'todos-procedimentos'
    ufs_str = '-'.join(ufs).lower()
    caminho_csv = dir_saida / f"previsao_producao_ambulatorial_{procs_str.lower()}_{ufs_str}.csv"
    df_previsao.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Previsão salva em: '{caminho_csv}'")

    titulo = f"Previsão de Produção Ambulatorial (Prophet) — {', '.join(ufs)}" + (f" (SIGTAP: {', '.join(proc_prefixos)})" if proc_prefixos else "")
    caminho_fig = dir_saida / f"previsao_producao_ambulatorial_{procs_str.lower()}_{ufs_str}.png"
    gerar_grafico_previsao_prophet(df_previsao, titulo, caminho_fig)
    print(f"📈 Gráfico salvo em: '{caminho_fig}'")

    print("\n" + "=" * 80)
    print("🎉 PREVISÃO DE PRODUÇÃO AMBULATORIAL CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prevê o volume mensal de produção ambulatorial (SIA/PA) com Prophet.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos-historico", dest="anos_historico", nargs="+", type=int, required=True, help="Anos de dados históricos (recomenda-se >= 2 anos).")
    parser.add_argument("--proc-prefixos", dest="proc_prefixos", nargs="+", default=[], help="Prefixos de código de procedimento SIGTAP (ex: 0304 = quimioterapia). Vazio = todos os procedimentos.")
    parser.add_argument("--meses-futuros", dest="meses_futuros", type=int, default=6, help="Nº de meses a prever no futuro.")
    parser.add_argument("--dir_saida", type=str, default="outputs/previsao_producao_ambulatorial", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
