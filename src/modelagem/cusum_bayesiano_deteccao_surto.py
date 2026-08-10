# -*- coding: utf-8 -*-
"""
======================================================================
  DETECÇÃO BAYESIANA DE MUDANÇA DE PATAMAR (SURTO) EM SÉRIE DE CASOS
======================================================================
Este script ajusta um modelo Bayesiano de ponto de mudança (changepoint)
a uma série semanal de notificações de um agravo do SINAN: a taxa de
casos é modelada como uma transição suave entre dois patamares
(λ1 antes do surto, λ2 depois), com a SEMANA da mudança (τ) e sua
INCLINAÇÃO tratadas como parâmetros a estimar via MCMC (NUTS/numpyro).

Diferente do `pipeline_deteccao_surtos.py` (que usa Prophet para prever o
esperado e sinaliza semanas que excedem o intervalo de previsão), aqui o
objetivo é diferente e complementar: estimar a PROBABILIDADE POSTERIOR de
que um surto genuíno ocorreu (λ2 muito maior que λ1) e EM QUE SEMANA,
com intervalos de credibilidade — útil quando se quer quantificar a
incerteza da própria detecção, não só sinalizar picos pontuais.
"""

import argparse
import os
os.environ.setdefault("JAX_PLATFORMS", "cpu")

from pathlib import Path

import pandas as pd
import numpy as np
import jax
import jax.numpy as jnp
import numpyro
import numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS

UF_PARA_CODIGO_IBGE = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17',
    'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27',
    'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41',
    'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53',
}


def carregar_serie_semanal(dis_code: str, uf: str, anos: list) -> pd.DataFrame:
    """Baixa um agravo do SINAN (nacional, sem filtro de UF na API) e agrega em
    contagem semanal de notificações filtrada pela UF de residência."""
    from pysus.online_data.SINAN import SINAN

    sinan_db = SINAN().load()
    files = sinan_db.get_files(dis_code=dis_code, year=anos)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo SINAN/{dis_code} encontrado para {anos}.")
    downloaded = sinan_db.download(files)
    df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()

    codigo_uf = UF_PARA_CODIGO_IBGE[uf.upper()]
    df = df[df['ID_MN_RESI'].astype(str).str[:2] == codigo_uf].copy()

    col_data = 'DT_NOTIFIC' if 'DT_NOTIFIC' in df.columns else 'DT_SIN_PRI'
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
    df = df.dropna(subset=[col_data])

    serie = df.resample('W-MON', on=col_data).size().reset_index(name='CASOS')
    serie.rename(columns={col_data: 'SEMANA'}, inplace=True)
    serie['t'] = np.arange(len(serie), dtype=float)
    return serie


def modelo_changepoint(t, y=None, escala_lambda: float = 50.0):
    T = len(t)
    lambda1 = numpyro.sample('lambda1', dist.HalfNormal(escala_lambda))
    lambda2 = numpyro.sample('lambda2', dist.HalfNormal(escala_lambda))
    tau = numpyro.sample('tau', dist.Uniform(0, T))
    k = numpyro.sample('k', dist.HalfNormal(2.0))
    rate = lambda1 + (lambda2 - lambda1) * jax.nn.sigmoid(k * (t - tau))
    rate = jnp.clip(rate, min=1e-6)
    with numpyro.plate('semanas', T):
        numpyro.sample('y', dist.Poisson(rate), obs=y)


def ajustar_changepoint(serie: pd.DataFrame, num_warmup: int, num_samples: int, seed: int):
    t = serie['t'].values
    y = serie['CASOS'].values.astype(float)
    escala_lambda = max(float(y.max()), 5.0) * 2

    kernel = NUTS(modelo_changepoint)
    mcmc = MCMC(kernel, num_warmup=num_warmup, num_samples=num_samples, num_chains=1, progress_bar=True)
    mcmc.run(jax.random.PRNGKey(seed), t=t, y=y, escala_lambda=escala_lambda)
    return mcmc.get_samples(), mcmc


def gerar_grafico(serie: pd.DataFrame, amostras, dir_saida: Path, dis_code: str, uf: str):
    import matplotlib.pyplot as plt

    t = serie['t'].values
    t_grid = np.linspace(t.min(), t.max(), 200)
    lambda1 = np.array(amostras['lambda1'])
    lambda2 = np.array(amostras['lambda2'])
    tau = np.array(amostras['tau'])
    k = np.array(amostras['k'])

    rates = lambda1[:, None] + (lambda2[:, None] - lambda1[:, None]) / (1 + np.exp(-k[:, None] * (t_grid[None, :] - tau[:, None])))
    rate_media = rates.mean(axis=0)
    rate_p05 = np.percentile(rates, 5, axis=0)
    rate_p95 = np.percentile(rates, 95, axis=0)

    plt.figure(figsize=(12, 6))
    plt.bar(t, serie['CASOS'], color='#a6bddb', label='Casos observados/semana')
    plt.plot(t_grid, rate_media, color='#d73027', linewidth=2, label='Taxa estimada (posterior média)')
    plt.fill_between(t_grid, rate_p05, rate_p95, color='#d73027', alpha=0.2, label='Intervalo de credibilidade 90%')
    plt.axvline(np.median(tau), color='black', linestyle='--', label=f'Mediana de τ (semana {np.median(tau):.1f})')
    plt.title(f"Detecção Bayesiana de Mudança de Patamar — SINAN/{dis_code} em {uf}")
    plt.xlabel('Semana epidemiológica (índice sequencial)')
    plt.ylabel('Número de casos')
    plt.legend()
    caminho_fig = dir_saida / f"changepoint_bayesiano_{dis_code.lower()}_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando série semanal de SINAN/{args.dis_code} para {args.uf}/{args.anos} ---")
    serie = carregar_serie_semanal(args.dis_code, args.uf, args.anos)
    print(f"✅ Série com {len(serie)} semanas, {serie['CASOS'].sum()} casos totais.")

    if len(serie) < 10:
        print("❌ Série muito curta para uma detecção de changepoint confiável (mínimo recomendado: 10 semanas).")
        return

    print(f"\n--- [ETAPA 2] Ajustando modelo Bayesiano de mudança de patamar (NUTS/numpyro) ---")
    amostras, mcmc = ajustar_changepoint(serie, args.warmup, args.amostras, args.seed)
    mcmc.print_summary()

    razao = np.array(amostras['lambda2']) / np.maximum(np.array(amostras['lambda1']), 1e-6)
    prob_surto = float((razao > args.limiar_razao).mean())
    semana_mediana = float(np.median(amostras['tau']))
    semana_data = serie['SEMANA'].iloc[min(int(round(semana_mediana)), len(serie) - 1)]

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: DETECÇÃO BAYESIANA DE SURTO — SINAN/{args.dis_code} EM {args.uf} ---")
    print("=" * 80)
    print(f"P(λ2/λ1 > {args.limiar_razao}) = {prob_surto:.1%}  (probabilidade posterior de que o patamar mais que {'triplicou' if args.limiar_razao==3 else f'multiplicou por {args.limiar_razao}x'})")
    print(f"Semana estimada da mudança (mediana de τ): semana #{semana_mediana:.1f} (~{semana_data.date()})")
    print(f"λ1 (patamar anterior, média posterior): {float(np.mean(amostras['lambda1'])):.2f} casos/semana")
    print(f"λ2 (patamar posterior, média posterior): {float(np.mean(amostras['lambda2'])):.2f} casos/semana")
    if prob_surto > 0.8:
        print("🚨 ALERTA: Forte evidência Bayesiana de mudança de patamar compatível com surto.")
    elif prob_surto > 0.5:
        print("⚠️ Evidência moderada de mudança de patamar — monitorar de perto.")
    else:
        print("✅ Sem evidência forte de mudança de patamar significativa no período.")
    print("=" * 80)

    caminho_csv = dir_saida / f"changepoint_bayesiano_{args.dis_code.lower()}_{args.uf.lower()}.csv"
    resumo = pd.DataFrame([{
        'DIS_CODE': args.dis_code, 'UF': args.uf, 'PROB_SURTO': prob_surto,
        'SEMANA_MUDANCA_MEDIANA': semana_mediana, 'DATA_MUDANCA_APROX': semana_data,
        'LAMBDA1_MEDIA': float(np.mean(amostras['lambda1'])), 'LAMBDA2_MEDIA': float(np.mean(amostras['lambda2'])),
    }])
    resumo.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resumo salvo em: '{caminho_csv}'")

    gerar_grafico(serie, amostras, dir_saida, args.dis_code, args.uf)

    print("\n" + "=" * 80)
    print("🎉 DETECÇÃO BAYESIANA DE MUDANÇA DE PATAMAR CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecta mudanças de patamar (surtos) em série semanal de um agravo do SINAN via modelo Bayesiano de changepoint.")
    parser.add_argument("--dis-code", type=str, required=True, help="Código do agravo do SINAN (ex: DENG, CHIK).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados a considerar na série.")
    parser.add_argument("--limiar-razao", type=float, default=3.0, help="Razão λ2/λ1 considerada indicativa de surto (padrão: 3x).")
    parser.add_argument("--warmup", type=int, default=1000, help="Nº de iterações de warmup do MCMC.")
    parser.add_argument("--amostras", type=int, default=1000, help="Nº de amostras posteriores do MCMC.")
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatória.")
    parser.add_argument("--dir_saida", type=str, default="outputs/changepoint_bayesiano", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
