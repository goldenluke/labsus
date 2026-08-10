# -*- coding: utf-8 -*-
"""
======================================================================
  ESTIMAÇÃO BAYESIANA EM PEQUENAS ÁREAS (SHRINKAGE) DA TMI MUNICIPAL
======================================================================
Problema clássico de estatística em saúde pública: em municípios pequenos,
poucos nascimentos fazem a Taxa de Mortalidade Infantil "bruta" saltar de
forma instável (ex.: 1 óbito em 20 nascimentos = TMI de 50 por mil, um
número dramático mas estatisticamente pouco confiável). Este script ajusta
um modelo hierárquico Bayesiano (Poisson com efeito aleatório log-normal
por município, "partial pooling") via MCMC (NUTS/numpyro) que "encolhe"
(shrinkage) as taxas de municípios com poucos nascimentos em direção à
média da UF, e mantém taxas de municípios grandes praticamente intactas —
produzindo estimativas mais estáveis e defensáveis para ranqueamento e
priorização de políticas.
"""

import argparse
import os
os.environ.setdefault("JAX_PLATFORMS", "cpu")  # evita falhas de cuDNN em ambientes sem GPU configurada

from pathlib import Path

import pandas as pd
import numpy as np
import jax
import jax.numpy as jnp
import numpyro
import numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS

from pysus.online_data.SIM import download as download_sim
from pysus.online_data.SINASC import download as download_sinasc


def carregar_obitos_e_nascimentos(uf: str, ano: int) -> pd.DataFrame:
    """Baixa SIM (óbitos <1 ano) e SINASC (nascidos vivos) e agrega contagens por município."""
    print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
    sinasc = download_sinasc(states=uf, years=ano, groups=['DN'])
    df_sinasc = pd.concat([f.to_dataframe() for f in sinasc], ignore_index=True) if isinstance(sinasc, list) else sinasc.to_dataframe()

    print(f"[LOG] Baixando SIM para {uf}/{ano}...")
    sim = download_sim(states=uf, years=ano, groups=['CID10'])
    if isinstance(sim, list):
        if not sim:
            raise FileNotFoundError(f"Nenhum arquivo SIM disponível para {ano} (dado ainda não publicado).")
        df_sim = pd.concat([f.to_dataframe() for f in sim], ignore_index=True)
    else:
        df_sim = sim.to_dataframe()

    df_sim_infantil = df_sim[pd.to_numeric(df_sim['IDADE'], errors='coerce') < 401].copy()

    nascimentos = df_sinasc.groupby(df_sinasc['CODMUNRES'].astype(str).str[:6]).size().rename('NASCIMENTOS')
    obitos = df_sim_infantil.groupby(df_sim_infantil['CODMUNRES'].astype(str).str[:6]).size().rename('OBITOS_INFANTIS')

    df = pd.concat([nascimentos, obitos], axis=1).fillna(0)
    df['OBITOS_INFANTIS'] = df['OBITOS_INFANTIS'].astype(int)
    # reset_index() nomeia a nova coluna a partir do nome herdado pela chave
    # do groupby (a Series 'CODMUNRES'), não como 'index' — por isso o rename
    # tem que partir de 'CODMUNRES', senão vira um no-op silencioso.
    df = df[df['NASCIMENTOS'] > 0].reset_index().rename(columns={'CODMUNRES': 'cod_mun_ibge_6'})
    df['TMI_BRUTA'] = (df['OBITOS_INFANTIS'] / df['NASCIMENTOS']) * 1000
    return df


def modelo_hierarquico(nascimentos, obitos=None):
    """log(taxa_i) ~ Normal(mu, sigma); obitos_i ~ Poisson(taxa_i * nascimentos_i)."""
    mu = numpyro.sample('mu', dist.Normal(-3.0, 3.0))
    sigma = numpyro.sample('sigma', dist.HalfNormal(2.0))
    with numpyro.plate('municipios', len(nascimentos)):
        log_taxa = numpyro.sample('log_taxa', dist.Normal(mu, sigma))
        taxa = jnp.exp(log_taxa)
        lam = taxa * nascimentos
        numpyro.sample('obitos', dist.Poisson(lam), obs=obitos)


def ajustar_modelo_bayesiano(df: pd.DataFrame, num_warmup: int, num_samples: int, seed: int):
    nascimentos = df['NASCIMENTOS'].values.astype(float)
    obitos = df['OBITOS_INFANTIS'].values.astype(float)

    kernel = NUTS(modelo_hierarquico)
    mcmc = MCMC(kernel, num_warmup=num_warmup, num_samples=num_samples, num_chains=1, progress_bar=True)
    mcmc.run(jax.random.PRNGKey(seed), nascimentos=nascimentos, obitos=obitos)
    amostras = mcmc.get_samples()

    taxa_posterior = jnp.exp(amostras['log_taxa'])  # shape: (num_samples, n_municipios)
    df['TMI_BAYESIANA'] = np.array(taxa_posterior.mean(axis=0)) * 1000
    df['TMI_BAYESIANA_IC95_INFERIOR'] = np.array(jnp.percentile(taxa_posterior, 2.5, axis=0)) * 1000
    df['TMI_BAYESIANA_IC95_SUPERIOR'] = np.array(jnp.percentile(taxa_posterior, 97.5, axis=0)) * 1000
    return df, mcmc


def gerar_grafico_shrinkage(df: pd.DataFrame, dir_saida: Path, uf: str):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(9, 9))
    tamanho_pontos = 20 + (df['NASCIMENTOS'] / df['NASCIMENTOS'].max()) * 300
    plt.scatter(df['TMI_BRUTA'], df['TMI_BAYESIANA'], s=tamanho_pontos, alpha=0.6, edgecolor='k')
    limite_max = max(df['TMI_BRUTA'].max(), df['TMI_BAYESIANA'].max()) * 1.1
    plt.plot([0, limite_max], [0, limite_max], color='red', linestyle='--', label='Sem encolhimento (y=x)')
    media_uf = (df['OBITOS_INFANTIS'].sum() / df['NASCIMENTOS'].sum()) * 1000
    plt.axhline(media_uf, color='grey', linestyle=':', label=f'Média da UF ({media_uf:.2f})')
    plt.xlabel('TMI Bruta (por 1.000 nascidos vivos)')
    plt.ylabel('TMI Bayesiana / Suavizada (por 1.000 nascidos vivos)')
    plt.title(f'Efeito de Encolhimento Bayesiano (Shrinkage) — TMI Municipal em {uf}\n(tamanho do ponto = nº de nascimentos)')
    plt.legend()
    caminho_fig = dir_saida / f"shrinkage_bayesiano_tmi_{uf.lower()}.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico de encolhimento (shrinkage) salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando óbitos infantis e nascimentos para {args.uf}/{args.ano} ---")
    df = carregar_obitos_e_nascimentos(args.uf, args.ano)
    print(f"✅ {len(df)} municípios com nascimentos > 0.")

    print(f"\n--- [ETAPA 2] Ajustando modelo hierárquico Bayesiano (NUTS/numpyro) ---")
    df, mcmc = ajustar_modelo_bayesiano(df, args.warmup, args.amostras, args.seed)
    print("✅ Modelo ajustado com sucesso.")
    mcmc.print_summary()

    from src.utils.dataloaders import adicionar_nome_municipio
    df = adicionar_nome_municipio(df, 'cod_mun_ibge_6', args.populacao)

    print("\n" + "=" * 80)
    print(f"--- COMPARAÇÃO: TMI BRUTA vs. TMI BAYESIANA (SUAVIZADA) EM {args.uf}/{args.ano} ---")
    print("=" * 80)
    df_ordenado = df.sort_values('NASCIMENTOS')
    print("Municípios com MENOS nascimentos (maior instabilidade da taxa bruta, maior encolhimento esperado):")
    print(df_ordenado[['cod_mun_ibge_6', 'municipio', 'NASCIMENTOS', 'OBITOS_INFANTIS', 'TMI_BRUTA', 'TMI_BAYESIANA']].head(10).to_string(index=False))
    print("=" * 80)

    caminho_csv = dir_saida / f"tmi_bayesiana_{args.uf.lower()}_{args.ano}.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Resultado completo salvo em: '{caminho_csv}'")

    gerar_grafico_shrinkage(df, dir_saida, args.uf)

    print("\n" + "=" * 80)
    print("🎉 ESTIMAÇÃO BAYESIANA EM PEQUENAS ÁREAS CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estima a TMI municipal com suavização Bayesiana hierárquica (shrinkage).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano da coorte de nascimentos.")
    parser.add_argument("--warmup", type=int, default=1000, help="Nº de iterações de warmup do MCMC (NUTS).")
    parser.add_argument("--amostras", type=int, default=1000, help="Nº de amostras posteriores do MCMC (NUTS).")
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatória.")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada (usado para mapear nomes de município).")
    parser.add_argument("--dir_saida", type=str, default="outputs/bayes_pequenas_areas", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
