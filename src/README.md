# src/ — Ambiente de Pesquisa & Desenvolvimento (P&D)

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Este é o **laboratório de pesquisa e desenvolvimento** do LabSUS: o lugar onde indicadores, índices compostos e modelos estatísticos/machine learning são prototipados e validados sobre dados públicos de saúde (DATASUS e IBGE), antes de virarem pipelines servidos pela API.

Aqui o código é **modular e reutilizável**: um indicador escrito como feature pode ser executado para qualquer UF e ano, consolidado em CSV e depois replicado em `api/pipeline_indicadores/` para consumo em produção.

## Organização

| Pasta | Conteúdo |
| :--- | :--- |
| `features/` | 73 módulos de indicadores municipais de saúde |
| `indices/` | Índices compostos (CCI, HAE, HEI, HNFI, HSRI, HSSI, HVS, MECI, PHSI, TERI...) |
| `modelagem/` | 70+ scripts de modelagem: predição, sobrevivência, séries temporais, análise espacial, NLP, redes |
| `utils/` | Dataloaders, base populacional, plot, séries temporais, índices compostos |
| `config.py` | Registro central dos indicadores (`INDICADORES_MAP`, polaridade `high`/`low`) |

### features/ — indicadores

Cada módulo expõe uma função `processar_dados(ufs, anos, arquivo_populacao, **kwargs)` que baixa os dados via `pysus` (SIM, SINASC, SIH, CNES, SIA, SINAN), cruza com a base populacional (`utils/dataloaders.filtrar_populacao`) e retorna um DataFrame município x indicador.

Exemplos: mortalidade infantil, cobertura pré-natal, médicos por mil, partos cesáreos, causas mal definidas, internações por doenças crônicas, ICSAP, hanseníase, sífilis, arboviroses, tuberculose, DCNT, indicadores de saúde do trabalhador e vigilância de agravos de notificação.

### indices/ — índices compostos

Consomem os indicadores de `features/` para gerar pontuações sintéticas por município (ex.: CCI, HEI, HSSI, MECI), usadas em rankings e painéis.

### modelagem/ — análises avançadas

Catálogo de técnicas por tema (cada uma com script próprio em `modelagem/` e pipeline correspondente em `api/`):

| Tema | Exemplos de scripts |
| :--- | :--- |
| Risco e mortalidade | `modelo_risco_obito_materno`, `modelo_risco_obito_neonatal_precoce_tardio`, `modelo_risco_perinatal`, `prever_sobrevida_infantil` |
| Causalidade e avaliação | `diferencas_em_diferencas_politica_saude`, `descontinuidade_regressao_peso_nascer`, `simulador_impacto_politicas` |
| Séries temporais e surtos | `cusum_bayesiano_deteccao_surto`, `decomposicao_sazonal_arboviroses`, `excesso_mortalidade`, `deteccao_quebra_estrutural_obitos`, previsão de nascimentos/óbitos/produção ambulatorial |
| Análise espacial | `moran_autocorrelacao_mortalidade_infantil`, `moran_bivariado_ivs_mortalidade`, `lisa_clusters_agravos_sinan`, `hotspots_getis_ord_internacoes`, `difusao_espacial_surto_sinan`, `gerar_painel_geografico` |
| Clustering e perfis | `clusters`, `hdbscan_outliers_estabelecimentos`, `umap_hdbscan_perfis_municipais`, `indice_kotelchuck_adequacao_prenatal`, `classificacao_robson_cesarianas` |
| Redes e fluxos | `rede_coocorrencia_comorbidades`, `rede_bipartida_procedimento_estabelecimento`, `analise_fluxo_pacientes`, `fluxo_alta_complexidade_sia`, `fluxo_partos_sinasc` |
| NLP | `similaridade_semantica_relatos_acidentes_animais`, `classificacao_gravidade_texto_clinico`, `analise_topicos_sintomas_nlp`, `requalificador_causa_obito_nlp` |
| Aprendizado de máquina | `modelo_risco_readmissao_classificacao`, `modelo_risco_abandono_tb`, `isolation_forest_auditoria_financeira`, `previsao_custo_internacao`, `estimacao_bayesiana_pequenas_areas` |

## Fluxo de trabalho

1. **Download automatizado** via `pysus` (DATASUS) + base populacional do IBGE (`utils/populacao.py`).
2. **Cálculo de indicadores**: cada feature gera um `*.csv` município x indicador por UF/ano.
3. **Consolidação**: `integrar_indicadores.py` junta tudo em `indicadores_integrados_[uf]_[ano].csv`.
4. **Análise**: `modelagem/` aplica estatística/ML e gera painéis, mapas e gráficos (`utils/plot.py`).
5. **Promoção a produto**: o que valida aqui é adaptado para `api/pipeline_*` (Django + Celery) e exibido no frontend.

## Uso rápido

```bash
# 1. Instale as dependências (pysus, pandas, numpy, scikit-learn, statsmodels, geopandas, matplotlib)
pip install pysus pandas numpy scikit-learn statsmodels geopandas matplotlib

# 2. Gere a base populacional (uma vez por estado/ano de interesse)
python utils/populacao.py

# 3. Rode uma feature ajustando UFs/ano no topo do arquivo
python features/pre_natal.py

# 4. Consolide os indicadores
python integrar_indicadores.py

# 5. Rode a modelagem desejada
python modelagem/clusters.py
```

## Fontes de dados

- SIM, SINASC, CNES, SIH, SIA, SINAN (DATASUS via `pysus`).
- IBGE: Censo Demográfico 2022 e estimativas populacionais (spline).
- Malhas municipais e bases auxiliares em `referencia/`.