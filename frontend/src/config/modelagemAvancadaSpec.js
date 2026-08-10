// Espelho, no frontend, do SPEC usado para gerar as 30 apps Django de
// "Modelagem Avançada" (api/pipeline_<slug>/). Cada entrada aqui descreve
// os campos de um formulário de disparo (GenericPipelineTriggerForm) e do
// visualizador de resultados (GenericResultsViewer) para um modelo.
//
// tipo de campo: uf | ufs | ano | anos | text | texts | int | float | int_optional | file_csv
//
// `sobre`: parágrafo explicando a técnica/algoritmo (mesmo espírito do
// InfoCard "Sobre este modelo de IA" das pipelines históricas, ex.:
// PipelineDeteccaoSurtosPage — Prophet + canal endêmico).
// `comoInterpretar`: lista de pontos para o InfoCard "Como Interpretar os
// Resultados" no viewer, no mesmo espírito da DeteccaoSurtosViewerPage.

export const GRUPOS_MODELAGEM = {
    1: { label: 'Análise Espacial', descricao: 'Autocorrelação e clusters geográficos (Moran, LISA, Getis-Ord).' },
    2: { label: 'Bayesiano & GLM', descricao: 'Estimação bayesiana de pequenas áreas e modelos lineares generalizados.' },
    3: { label: 'Séries Temporais', descricao: 'Sazonalidade, quebras estruturais e excesso de mortalidade.' },
    4: { label: 'Sobrevivência', descricao: 'Kaplan-Meier e Cox aplicados a tratamento, internação e reincidência.' },
    5: { label: 'Redes & Grafos', descricao: 'Coocorrência de comorbidades e especialização de estabelecimentos.' },
    6: { label: 'Inferência Causal', descricao: 'Diferenças-em-diferenças e descontinuidade de regressão.' },
    7: { label: 'NLP Avançado', descricao: 'Classificação e similaridade semântica sobre texto clínico livre.' },
    8: { label: 'Detecção de Anomalias', descricao: 'Isolation Forest e HDBSCAN para outliers de produção/estabelecimento.' },
    9: { label: 'Redução de Dimensionalidade', descricao: 'UMAP, HDBSCAN e Análise Fatorial sobre painéis de indicadores.' },
    10: { label: 'Alto Impacto (Triagem Clínica)', descricao: 'Modelos de risco e classificação para triagem em saúde materno-infantil.' },
};

export const MODELAGEM_AVANCADA_SPEC = [
    { key: 'moran-mortalidade', title: 'Moran Global: Mortalidade Infantil', grupo: 1,
      descricao: 'Mede se municípios com mortalidade infantil alta/baixa se agrupam espacialmente (Índice de Moran Global).',
      sobre: 'Este modelo usa o Índice de Moran Global (esda/libpysal) para testar se municípios com Taxa de Mortalidade Infantil (TMI) parecida estão geograficamente próximos — ou se a distribuição espacial é aleatória. Constrói uma matriz de vizinhança (contiguidade rainha) a partir dos limites municipais e compara o valor observado de Moran\'s I contra uma distribuição gerada por permutações aleatórias dos dados, obtendo um p-valor empírico (pseudo p-valor).',
      comoInterpretar: [
          'Moran\'s I próximo de +1: forte autocorrelação espacial positiva — municípios com TMI parecida estão agrupados (cluster).',
          'Moran\'s I próximo de 0: distribuição espacialmente aleatória, sem padrão geográfico.',
          'Moran\'s I próximo de -1: padrão de tabuleiro de xadrez (municípios vizinhos com valores opostos).',
          'p-valor < 0.05: o padrão observado é estatisticamente significante e dificilmente seria fruto do acaso.',
      ],
      campos: [
          { nome: 'painel_csv', tipo: 'file_csv', label: 'Painel de Indicadores (CSV)', default: null, obrigatorio: true },
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'indicador', tipo: 'text', label: 'Indicador (coluna)', default: 'TMI', obrigatorio: false },
          { nome: 'permutacoes', tipo: 'int', label: 'Permutações', default: 999, obrigatorio: false },
      ] },
    { key: 'lisa-sinan', title: 'LISA: Clusters de Agravo SINAN', grupo: 1,
      descricao: 'Identifica clusters (alto-alto, baixo-baixo) e outliers espaciais de notificações de um agravo.',
      sobre: 'Diferente do Moran Global (que dá um único número para toda a UF), o LISA (Local Indicators of Spatial Association) calcula um índice de autocorrelação PARA CADA MUNICÍPIO, classificando-o em um de quatro quadrantes: Alto-Alto (cluster de risco), Baixo-Baixo (cluster protetor), Alto-Baixo e Baixo-Alto (outliers espaciais). Usa dados reais do SINAN para o agravo escolhido e testa a significância de cada município por permutação.',
      comoInterpretar: [
          'Alto-Alto: município com valor alto rodeado de vizinhos também com valor alto — um cluster de risco a ser priorizado.',
          'Baixo-Baixo: município com valor baixo rodeado de vizinhos também baixos — um cluster protetor.',
          'Alto-Baixo / Baixo-Alto: outliers espaciais — o município destoa da vizinhança, merece investigação (ex.: subnotificação vizinha ou surto localizado).',
          'Municípios sem classificação não têm padrão espacial claro no nível de confiança escolhido.',
      ],
      campos: [
          { nome: 'dis_code', tipo: 'text', label: 'Código do Agravo (SINAN)', default: 'ANIM', obrigatorio: true },
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'significancia', tipo: 'float', label: 'Significância (p-valor)', default: 0.05, obrigatorio: false },
          { nome: 'permutacoes', tipo: 'int', label: 'Permutações', default: 999, obrigatorio: false },
      ] },
    { key: 'hotspots-internacao', title: 'Getis-Ord: Hotspots de Internação', grupo: 1,
      descricao: 'Detecta hotspots/coldspots estatisticamente significativos de internações por CID-10.',
      sobre: 'Aplica a estatística Getis-Ord Gi* (esda) sobre a contagem de internações filtradas por prefixo de CID-10, identificando hotspots (concentrações estatisticamente significantes de alta internação) e coldspots (baixa internação) entre municípios vizinhos. Diferente do LISA, o Gi* soma os valores DENTRO da vizinhança de cada município, sendo mais sensível a concentrações absolutas do que a diferenças relativas.',
      comoInterpretar: [
          'Hotspot (Z-score alto e positivo): região onde o município e seus vizinhos têm internações consistentemente acima da média — candidato a reforço de capacidade assistencial.',
          'Coldspot (Z-score baixo e negativo): concentração de baixa utilização — pode indicar barreira de acesso ou baixa incidência real.',
          'Município sem classificação: nem hotspot nem coldspot no nível de significância escolhido.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'cids', tipo: 'texts', label: 'Prefixos de CID-10', default: ['J45'], obrigatorio: false },
          { nome: 'significancia', tipo: 'float', label: 'Significância (p-valor)', default: 0.05, obrigatorio: false },
          { nome: 'permutacoes', tipo: 'int', label: 'Permutações', default: 999, obrigatorio: false },
      ] },
    // oculto: pouca utilidade demonstrada em uso real — mantido no SPEC (e
    // com backend/rotas intactos) só para não quebrar links/resultados já
    // gerados, mas fora da Sidebar/HomePage (ver filtro em pipelineCatalog.js).
    { key: 'moran-bivariado', title: 'Moran Bivariado: IVS x Mortalidade', grupo: 1, oculto: true,
      descricao: 'Correlação espacial entre um índice de vulnerabilidade social e um indicador de mortalidade.',
      sobre: 'Versão bivariada do Índice de Moran: em vez de comparar um indicador com ele mesmo no espaço, mede se o Índice de Vulnerabilidade Social (IVS) de um município está espacialmente correlacionado com o indicador de mortalidade dos municípios VIZINHOS. Um Moran bivariado positivo sugere que áreas vulneráveis tendem a estar cercadas de áreas com mortalidade elevada — evidência de efeito de vizinhança/contágio territorial da vulnerabilidade.',
      comoInterpretar: [
          'Moran bivariado positivo: vulnerabilidade social (IVS) de um município acompanha mortalidade elevada nos municípios vizinhos.',
          'Moran bivariado próximo de zero: os dois fenômenos não parecem espacialmente associados.',
          'Como no Moran Global, o p-valor (por permutação) indica se o padrão é estatisticamente robusto.',
      ],
      campos: [
          { nome: 'geo_csv', tipo: 'file_csv', label: 'Painel Geográfico com IVS (CSV)', default: null, obrigatorio: true },
          { nome: 'indicadores_csv', tipo: 'file_csv', label: 'Painel de Indicadores — precisa incluir TMI (CSV)', default: null, obrigatorio: true },
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'permutacoes', tipo: 'int', label: 'Permutações', default: 999, obrigatorio: false },
      ] },

    { key: 'gerar-painel-geografico', title: 'Gerar Painel Geográfico (IVS + CNES)', grupo: 1, oculto: true,
      descricao: 'Consolida o Índice de Vulnerabilidade Social (IPEA) com a contagem de UBS do CNES, por município — pré-requisito do Moran Bivariado: IVS x Mortalidade.',
      sobre: 'Este módulo não é um modelo estatístico, é um pipeline de consolidação de dados: junta o Índice de Vulnerabilidade Social (IVS, IPEA, já incluído na plataforma por UF) com a contagem de Unidades Básicas de Saúde (UBS) do CNES, produzindo um único painel por município com a coluna "ivs" — o arquivo de entrada que o Moran Bivariado: IVS x Mortalidade pede em "Painel Geográfico com IVS (CSV)". Rode este módulo primeiro, selecione o CSV gerado aqui como entrada lá.',
      comoInterpretar: [
          'A saída é um CSV de município x (IVS, N_UBS) — não há resultado estatístico para interpretar aqui.',
          'Use o arquivo gerado como entrada do campo "Painel Geográfico com IVS (CSV)" no Moran Bivariado: IVS x Mortalidade.',
          'Se um município não aparece no resultado, o CSV de IVS daquela UF pode não cobrir esse município, ou o CNES não retornou dados para o ano escolhido.',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano (referência CNES)', default: 2022, obrigatorio: true },
      ] },

    { key: 'bayes-pequenas-areas', title: 'Bayesiano: Pequenas Áreas', grupo: 2,
      descricao: 'Estimação bayesiana (encolhimento) de taxas em municípios com poucos eventos.',
      sobre: 'Em municípios com poucos eventos, a taxa bruta observada é estatisticamente instável (um único caso a mais/menos muda drasticamente a taxa). Este modelo usa MCMC (numpyro) para "encolher" (shrink) as taxas municipais em direção à média regional, ponderando pela quantidade de dados disponível em cada município — municípios com poucos dados são puxados mais fortemente para a média, municípios com muitos dados mantêm sua taxa observada.',
      comoInterpretar: [
          'Taxa bruta: cálculo direto (casos/população), instável em municípios pequenos.',
          'Taxa suavizada (bayesiana): versão ajustada, mais confiável para comparar municípios de tamanhos diferentes.',
          'Intervalo de credibilidade: faixa de incerteza da estimativa bayesiana — quanto mais estreito, mais confiança no valor.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'warmup', tipo: 'int', label: 'Warmup (MCMC)', default: 1000, obrigatorio: false },
          { nome: 'amostras', tipo: 'int', label: 'Amostras (MCMC)', default: 1000, obrigatorio: false },
          { nome: 'seed', tipo: 'int', label: 'Semente', default: 42, obrigatorio: false },
      ] },
    { key: 'changepoint-bayesiano', title: 'Bayesiano: Changepoint de Surto', grupo: 2,
      descricao: 'Detecta o ponto de mudança bayesiano em que a taxa de notificações salta de um patamar a outro.',
      sobre: 'Detecta, de forma bayesiana (numpyro/MCMC), a semana em que a taxa de notificações de um agravo muda de um patamar baixo (λ1) para um patamar alto (λ2), modelando a transição como uma sigmoide no tempo. Diferente de um limiar fixo, o modelo estima a probabilidade de cada semana ser o ponto de mudança (tau) e a razão entre os dois patamares — só sinaliza surto se essa razão superar o limiar definido.',
      comoInterpretar: [
          'tau: semana estimada em que a série mudou de patamar (o "changepoint").',
          'λ1 / λ2: taxa média de notificações antes/depois do changepoint.',
          'Razão λ2/λ1: quantas vezes a taxa aumentou; comparada ao limiar definido para decidir se caracteriza surto.',
          'Intervalo de credibilidade de tau: quanto mais estreito, mais precisa é a estimativa de quando o surto começou.',
      ],
      campos: [
          { nome: 'dis_code', tipo: 'text', label: 'Código do Agravo (SINAN)', default: 'DENG', obrigatorio: true },
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022, 2023], obrigatorio: true },
          { nome: 'limiar_razao', tipo: 'float', label: 'Limiar de Razão (λ2/λ1)', default: 3.0, obrigatorio: false },
          { nome: 'warmup', tipo: 'int', label: 'Warmup (MCMC)', default: 1000, obrigatorio: false },
          { nome: 'amostras', tipo: 'int', label: 'Amostras (MCMC)', default: 1000, obrigatorio: false },
          { nome: 'seed', tipo: 'int', label: 'Semente', default: 42, obrigatorio: false },
      ] },
    { key: 'binomial-negativa', title: 'GLM Binomial Negativa: Internação', grupo: 2,
      descricao: 'Modela contagens de internação superdispersas em função de determinantes municipais.',
      sobre: 'Regressão Binomial Negativa (GLM, statsmodels): modela a contagem de internações por um CID como função de determinantes municipais (Índice de Vulnerabilidade Social, densidade de UBS por 10 mil habitantes). Usada no lugar de uma Poisson comum porque contagens de saúde pública tipicamente têm superdispersão (variância maior que a média), o que a Binomial Negativa acomoda nativamente.',
      comoInterpretar: [
          'Coeficiente positivo: o determinante aumenta o número esperado de internações.',
          'Coeficiente negativo: o determinante está associado a menos internações (efeito protetor).',
          'IRR (Razão de Taxas de Incidência) = exp(coeficiente): quanto a taxa de internação multiplica para cada unidade do determinante.',
          'p-valor < 0.05: a associação é estatisticamente significante nesta amostra.',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'cids', tipo: 'texts', label: 'Prefixos de CID-10', default: ['J45'], obrigatorio: false },
      ] },

    { key: 'stl-sarima-arboviroses', title: 'STL+SARIMA: Arboviroses', grupo: 3,
      descricao: 'Decompõe a série de notificações em tendência/sazonalidade e projeta meses futuros com SARIMA.',
      sobre: 'Decompõe a série mensal de notificações de um agravo (STL — Seasonal-Trend decomposition using Loess) em três componentes: tendência de longo prazo, sazonalidade anual e resíduo, e depois ajusta um modelo SARIMA sobre a série para projetar os próximos meses. Útil para antecipar picos sazonais esperados de arboviroses (dengue, chikungunya, zika) e planejar a resposta com antecedência.',
      comoInterpretar: [
          'Tendência: direção de longo prazo da série, sem o efeito da sazonalidade.',
          'Sazonalidade: padrão que se repete todo ano (ex.: pico de dengue no verão).',
          'Previsão (meses futuros): projeção SARIMA, com intervalo de confiança.',
          'Resíduo grande em algum mês: esse mês fugiu do padrão esperado por tendência+sazonalidade — candidato a investigação (surto atípico).',
      ],
      campos: [
          { nome: 'dis_code', tipo: 'text', label: 'Código do Agravo (SINAN)', default: 'DENG', obrigatorio: false },
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2020, 2021, 2022, 2023], obrigatorio: true },
          { nome: 'meses_futuros', tipo: 'int', label: 'Meses a Prever', default: 6, obrigatorio: false },
      ] },
    { key: 'previsao-obitos', title: 'Previsão de Óbitos (Prophet)', grupo: 3,
      descricao: 'Projeta a série mensal de óbitos (SIM) com Prophet, opcionalmente filtrada por causa (CID-10).',
      sobre: 'Mesma lógica do módulo "Previsão de Internações" (SIH), aplicada ao SIM: agrega a série mensal de óbitos — de todas as causas ou de um CID-10 específico — e ajusta um modelo Prophet (tendência + sazonalidade anual) para projetar os próximos meses com intervalo de incerteza. Diferente de "Excesso de Mortalidade" (que compara o observado contra uma linha de base já ocorrida), este módulo projeta o que ainda não aconteceu.',
      comoInterpretar: [
          'Observado (y): contagem mensal real de óbitos, até o último mês com dado publicado.',
          'Previsão (yhat): projeção do Prophet para os meses futuros, com faixa de incerteza (yhat_lower/yhat_upper).',
          'Sazonalidade anual: picos recorrentes em certos meses (ex.: causas respiratórias no inverno) são capturados automaticamente pelo modelo.',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'anos_historico', tipo: 'anos', label: 'Anos Históricos', default: [2020, 2021, 2022, 2023], obrigatorio: true },
          { nome: 'cid_prefixos', tipo: 'texts', label: 'Prefixos de CID-10 (opcional)', default: [], obrigatorio: false },
          { nome: 'meses_futuros', tipo: 'int', label: 'Meses a Prever', default: 6, obrigatorio: false },
      ] },
    { key: 'previsao-nascimentos', title: 'Previsão de Nascimentos (Prophet)', grupo: 3,
      descricao: 'Projeta a série mensal de nascimentos (SINASC) com Prophet — planejamento de leitos obstétricos/neonatais.',
      sobre: 'Mesma lógica do módulo "Previsão de Internações" (SIH), aplicada ao SINASC: agrega a série mensal de nascidos vivos e ajusta um modelo Prophet (tendência + sazonalidade anual) para projetar os próximos meses com intervalo de incerteza — insumo direto para dimensionar leitos obstétricos/UTI neonatal e equipe de maternidade com antecedência, em vez de reagir à demanda já realizada.',
      comoInterpretar: [
          'Observado (y): contagem mensal real de nascimentos, até o último mês com dado publicado.',
          'Previsão (yhat): projeção do Prophet para os meses futuros, com faixa de incerteza (yhat_lower/yhat_upper).',
          'Use a previsão para antecipar picos sazonais de demanda por leito obstétrico/neonatal, não apenas reagir à ocupação atual.',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'anos_historico', tipo: 'anos', label: 'Anos Históricos', default: [2020, 2021, 2022, 2023], obrigatorio: true },
          { nome: 'meses_futuros', tipo: 'int', label: 'Meses a Prever', default: 6, obrigatorio: false },
      ] },
    { key: 'previsao-producao-ambulatorial', title: 'Previsão de Produção Ambulatorial (Prophet)', grupo: 3,
      descricao: 'Projeta o volume mensal de procedimentos ambulatoriais (SIA/SIGTAP) com Prophet — planejamento orçamentário/de agenda.',
      sobre: 'Mesma lógica do módulo "Previsão de Internações" (SIH), aplicada ao SIA/PA: agrega o volume mensal de procedimentos ambulatoriais aprovados — todos ou filtrados por prefixo de código SIGTAP — e ajusta um modelo Prophet (tendência + sazonalidade anual) para projetar os próximos meses. Útil para planejamento orçamentário e de agenda ambulatorial (ex.: antecipar picos de demanda por quimioterapia, fisioterapia, exames).',
      comoInterpretar: [
          'Observado (y): volume mensal real de procedimentos aprovados, até a última competência publicada.',
          'Previsão (yhat): projeção do Prophet para os meses futuros, com faixa de incerteza (yhat_lower/yhat_upper).',
          'Filtre por prefixo SIGTAP para prever um tipo específico de procedimento em vez do volume total.',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'anos_historico', tipo: 'anos', label: 'Anos Históricos', default: [2022, 2023], obrigatorio: true },
          { nome: 'proc_prefixos', tipo: 'texts', label: 'Prefixos SIGTAP (opcional)', default: [], obrigatorio: false },
          { nome: 'meses_futuros', tipo: 'int', label: 'Meses a Prever', default: 6, obrigatorio: false },
      ] },
    { key: 'quebra-estrutural', title: 'Quebra Estrutural: Óbitos (Teste de Chow)', grupo: 3,
      descricao: 'Testa se a série de óbitos por CID-10 sofreu uma mudança estrutural de patamar/tendência.',
      sobre: 'Teste de Chow: testa estatisticamente se a série temporal de óbitos por um CID sofreu uma mudança estrutural — um ponto em que o comportamento da série (nível ou tendência) muda de forma abrupta e permanente, diferente de uma flutuação normal. Testa cada ano candidato como possível ponto de quebra e reporta o de maior significância estatística.',
      comoInterpretar: [
          'Ano de quebra estrutural identificado: ponto em que a série "antes" e "depois" se comportam de forma estatisticamente diferente.',
          'Estatística F e p-valor: quanto menor o p-valor, mais forte a evidência de que houve realmente uma quebra (não é só ruído).',
          'Compare o nível médio antes/depois da quebra para entender se a mudança foi de aumento ou redução na mortalidade.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022], obrigatorio: true },
          { nome: 'cids', tipo: 'texts', label: 'Prefixos de CID-10', default: ['I2'], obrigatorio: false },
          { nome: 'significancia', tipo: 'float', label: 'Significância (p-valor)', default: 0.05, obrigatorio: false },
      ] },
    { key: 'excesso-mortalidade', title: 'Excesso de Mortalidade', grupo: 3,
      descricao: 'Compara óbitos observados num período de avaliação contra a linha de base esperada.',
      sobre: 'Calcula o "excesso de mortalidade": constrói uma linha de base esperada de óbitos a partir de um período de referência (anos-base, sem eventos atípicos) e compara com os óbitos observados no período de avaliação. A diferença — óbitos observados menos óbitos esperados — é o excesso de mortalidade, uma medida direta e interpretável do impacto de um evento (epidemia, desastre etc.), mais robusta que olhar apenas a causa-básica registrada.',
      comoInterpretar: [
          'Excesso de mortalidade positivo: mais óbitos ocorreram do que o esperado pela linha de base histórica.',
          'Excesso de mortalidade negativo (raro): menos óbitos que o esperado.',
          'Excesso relativo (%): o quanto os óbitos observados superaram o esperado, em termos percentuais — mais fácil de comparar entre municípios de tamanhos diferentes.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos_base', tipo: 'anos', label: 'Anos do Período-Base', default: [2017, 2018, 2019], obrigatorio: true },
          { nome: 'anos_avaliacao', tipo: 'anos', label: 'Anos a Avaliar', default: [2020, 2021], obrigatorio: true },
          { nome: 'cids', tipo: 'texts', label: 'Prefixos de CID-10 (opcional)', default: [], obrigatorio: false },
      ] },

    { key: 'sobrevida-tb', title: 'Sobrevida: Tratamento de Tuberculose', grupo: 4,
      descricao: 'Curvas de Kaplan-Meier para tempo até cura/óbito/abandono do tratamento de TB, por estrato.',
      sobre: 'Curvas de Kaplan-Meier (lifelines): estimam, a partir de dados reais do SINAN/Tuberculose, a probabilidade de um paciente permanecer em tratamento (sem desfecho de cura, óbito ou abandono) ao longo do tempo, estratificado por uma variável categórica (ex.: sexo). É o método padrão em epidemiologia para estimar curvas de sobrevida com dados censurados (pacientes ainda em tratamento ao final do período de observação).',
      comoInterpretar: [
          'Curva de Kaplan-Meier: no eixo Y, a probabilidade acumulada de ainda não ter tido o desfecho; no eixo X, o tempo desde o início do tratamento.',
          'Quedas na curva: momentos em que desfechos (cura, óbito, abandono) aconteceram.',
          'Comparar curvas entre estratos: estratos com curva mais alta têm melhor retenção/desfecho no tratamento.',
      ],
      campos: [
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2021, 2022, 2023], obrigatorio: false },
          { nome: 'estrato', tipo: 'text', label: 'Coluna de Estrato', default: 'CS_SEXO', obrigatorio: false },
      ] },
    { key: 'sobrevida-permanencia', title: 'Sobrevida: Permanência Hospitalar', grupo: 4,
      descricao: 'Tempo até a alta hospitalar tratado como evento de sobrevivência (Kaplan-Meier/Cox).',
      sobre: 'Trata o tempo de internação até a alta hospitalar como um evento de sobrevivência (Kaplan-Meier/Cox — lifelines), em vez de apenas calcular uma média de dias. Essa abordagem lida corretamente com internações ainda em curso (censura) e permite comparar o "risco instantâneo de alta" entre diferentes CIDs ou perfis de paciente ao longo da internação.',
      comoInterpretar: [
          'Curva de sobrevida da permanência: probabilidade de o paciente ainda estar internado após X dias.',
          'Queda rápida no início: a maioria dos pacientes recebe alta cedo (curta permanência).',
          'Cauda longa: um subgrupo permanece internado por muito mais tempo — merece atenção para gestão de leitos.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022], obrigatorio: true },
          { nome: 'cids', tipo: 'texts', label: 'Prefixos de CID-10 (opcional)', default: [], obrigatorio: false },
      ] },
    { key: 'sobrevida-reincidencia', title: 'Sobrevida: Reincidência por Causa Externa', grupo: 4,
      descricao: 'Tempo até uma nova internação por causa externa (acidentes, violência) após a primeira.',
      sobre: 'Mede o tempo até uma nova internação por causa externa (acidentes, violência, lesões autoprovocadas) após a primeira, usando Kaplan-Meier. Ajuda a identificar o período de maior risco de reincidência após a alta — informação útil para desenhar janelas de intervenção (ex.: encaminhamento psicossocial, prevenção de violência).',
      comoInterpretar: [
          'Curva de sobrevida: probabilidade de o paciente ainda não ter tido uma reincidência após X dias da primeira internação.',
          'Queda acentuada logo nos primeiros meses: sinal de que a reincidência tende a ser precoce — janela crítica para intervenção.',
          'Pacientes sem reincidência registrada entram como "censurados" (não significa que nunca vão reincidir, só que não foi observado até o fim dos dados).',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2021, 2022], obrigatorio: true },
      ] },

    { key: 'rede-comorbidades', title: 'Rede: Coocorrência de Comorbidades', grupo: 5,
      descricao: 'Grafo de comorbidades que aparecem juntas nas mesmas internações.',
      sobre: 'Constrói um grafo de comorbidades (NetworkX) a partir de internações reais: cada nó é um CID-10, e uma aresta conecta dois CIDs que aparecem juntos na mesma internação (diagnóstico principal + secundários) com frequência mínima. O peso da aresta é o número de coocorrências. Revela quais combinações de doenças costumam andar juntas na população — útil para linhas de cuidado integradas.',
      comoInterpretar: [
          'Nós maiores/mais centrais: comorbidades mais frequentes e mais conectadas a outras.',
          'Arestas mais grossas: pares de CID-10 que coocorrem com mais frequência.',
          'Comunidades/clusters no grafo: grupos de comorbidades que tendem a aparecer juntas — podem sugerir uma síndrome ou perfil de paciente comum.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022], obrigatorio: true },
          { nome: 'cid_coorte', tipo: 'texts', label: 'Coorte por CID-10 (opcional)', default: [], obrigatorio: false },
          { nome: 'min_frequencia_no', tipo: 'int', label: 'Frequência Mínima do Nó', default: 20, obrigatorio: false },
          { nome: 'min_peso_aresta', tipo: 'int', label: 'Peso Mínimo da Aresta', default: 5, obrigatorio: false },
      ] },
    { key: 'rede-especializacao', title: 'Rede: Especialização de Estabelecimentos', grupo: 5,
      descricao: 'Rede bipartida procedimento-estabelecimento para mapear especialização assistencial.',
      sobre: 'Rede bipartida (NetworkX) conectando estabelecimentos de saúde a procedimentos que eles realizam, com peso pela produção (nº de registros no SIA/SIH). Permite identificar o grau de especialização de cada estabelecimento (poucos procedimentos concentrados vs. produção diversificada) e mapear a rede de referência assistencial de uma UF.',
      comoInterpretar: [
          'Estabelecimento com poucas conexões e alto peso: altamente especializado num procedimento específico.',
          'Estabelecimento com muitas conexões: atua como generalista, cobrindo uma ampla carteira de procedimentos.',
          'Procedimentos com poucos estabelecimentos conectados: concentração de oferta — risco de gargalo se esses estabelecimentos ficarem indisponíveis.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'min_producao_procedimento', tipo: 'int', label: 'Produção Mínima (Procedimento)', default: 50, obrigatorio: false },
          { nome: 'min_producao_estabelecimento', tipo: 'int', label: 'Produção Mínima (Estabelecimento)', default: 50, obrigatorio: false },
      ] },

    { key: 'diff-in-diff', title: 'Diferenças-em-Diferenças', grupo: 6,
      descricao: 'Efeito causal de uma intervenção comparando municípios tratados vs. controle antes/depois.',
      sobre: 'Diferenças-em-Diferenças (DiD): método causal clássico que compara a mudança no indicador antes/depois de uma intervenção entre municípios que a receberam (tratados) e municípios que não receberam (controle), isolando o efeito da intervenção de tendências gerais que afetariam todos os municípios de qualquer forma. Requer um painel multi-ano do mesmo indicador.',
      comoInterpretar: [
          'Efeito DiD: a diferença extra que os municípios tratados tiveram, além da tendência já compartilhada com o grupo controle — essa é a estimativa do efeito causal da intervenção.',
          'Pré-tendências paralelas: se os grupos tratado/controle já se moviam de forma muito diferente ANTES da intervenção, o resultado fica menos confiável.',
          'p-valor/intervalo de confiança do efeito: indicam se o efeito estimado é estatisticamente distinguível de zero.',
      ],
      campos: [
          { nome: 'painel_csv', tipo: 'file_csv', label: 'Painel de Indicadores Multi-Ano (CSV)', default: null, obrigatorio: true },
          { nome: 'indicador', tipo: 'text', label: 'Indicador (coluna, desfecho)', default: 'TMI', obrigatorio: true },
          { nome: 'municipios_tratados', tipo: 'texts', label: 'Municípios Tratados (cód. IBGE 6 díg.)', default: [], obrigatorio: true },
          { nome: 'ano_intervencao', tipo: 'int', label: 'Ano da Intervenção', default: 2022, obrigatorio: true },
      ] },
    { key: 'rdd-peso-nascer', title: 'RDD: Limiar de Peso ao Nascer', grupo: 6,
      descricao: 'Descontinuidade de regressão em torno de um limiar de peso ao nascer (ex.: 2500g).',
      sobre: 'Descontinuidade de Regressão (RDD): explora um limiar clínico de peso ao nascer (ex.: 2.500g, definição de baixo peso) como um "experimento natural" — bebês logo abaixo e logo acima do limiar são, em média, muito parecidos em tudo, exceto por cruzarem (ou não) o limiar que costuma disparar protocolos clínicos diferenciados. Compara desfechos dentro de uma banda estreita ao redor do limiar para estimar o efeito causal de cruzá-lo.',
      comoInterpretar: [
          'Salto (descontinuidade) no desfecho exatamente no limiar: evidência de que cruzar o limiar de peso muda o desfecho, plausivelmente pelo protocolo clínico associado.',
          'Ausência de salto: o limiar não parece ter efeito causal detectável no desfecho analisado, dentro da banda testada.',
          'Banda (largura da janela ao redor do limiar): bandas mais estreitas comparam bebês mais parecidos, mas com menos dados (maior incerteza).',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'banda', tipo: 'int', label: 'Banda (gramas)', default: 300, obrigatorio: false },
      ] },

    { key: 'gravidade-texto', title: 'NLP: Gravidade por Texto Clínico', grupo: 7,
      descricao: 'Classifica a gravidade de um caso a partir do texto clínico livre (campos de descrição do SINAN).',
      sobre: 'Processa o texto clínico livre (campos de descrição de sintomas do SINAN) com TF-IDF e um classificador para estimar a gravidade do caso, sem depender de campos estruturados que muitas vezes vêm incompletos. Útil para triagem automática de relatos textuais e para identificar padrões de linguagem associados a casos mais graves.',
      comoInterpretar: [
          'Classe de gravidade atribuída: rótulo previsto pelo modelo a partir do texto do caso.',
          'Termos mais associados a cada classe: palavras que o modelo aprendeu a associar a maior/menor gravidade — úteis para auditoria do modelo.',
          'Casos sem texto clínico suficiente são excluídos da análise (não há como avaliar gravidade sem descrição).',
      ],
      campos: [
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2021, 2022, 2023], obrigatorio: true },
      ] },
    { key: 'similaridade-relatos', title: 'NLP: Similaridade de Relatos', grupo: 7,
      descricao: 'Agrupa relatos de acidentes com animais peçonhentos por similaridade semântica do texto.',
      sobre: 'Vetoriza (TF-IDF) os relatos de texto livre de acidentes por animais peçonhentos e agrupa (KMeans) os relatos mais parecidos entre si em clusters narrativos — por exemplo, um cluster pode capturar relatos de picada de serpente ("dor local, edema, equimose") enquanto outro captura picada de escorpião ("dor intensa, sudorese, taquicardia"). Diferente de modelagem de tópicos, aqui cada relato pertence a um único cluster.',
      comoInterpretar: [
          'Cada ponto no gráfico de dispersão é um relato, projetado em 2D (SVD/LSA) a partir do texto — pontos próximos têm linguagem parecida.',
          'Cores/clusters: agrupamentos narrativos encontrados pelo KMeans.',
          'Termos mais frequentes de cada cluster: palavras-chave que caracterizam aquele padrão de relato (ex.: "padrão serpente" vs. "padrão escorpião").',
      ],
      campos: [
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2021, 2022, 2023], obrigatorio: true },
          { nome: 'n_clusters', tipo: 'int', label: 'Nº de Clusters', default: 6, obrigatorio: false },
          { nome: 'seed', tipo: 'int', label: 'Semente', default: 42, obrigatorio: false },
      ] },

    { key: 'isolation-forest', title: 'Isolation Forest: Auditoria Financeira', grupo: 8,
      descricao: 'Sinaliza procedimentos com valores/quantidades atípicas para priorizar auditoria.',
      sobre: 'Isolation Forest (scikit-learn): algoritmo de detecção de anomalias que isola observações atípicas construindo árvores de decisão aleatórias — anomalias, por serem raras e diferentes, tendem a ser isoladas com poucos cortes, enquanto pontos normais exigem muitos cortes. Aplicado sobre valores e quantidades de procedimentos do SIH/SIA para sinalizar registros financeiramente atípicos e priorizar auditoria.',
      comoInterpretar: [
          'Score de anomalia mais negativo: quanto mais "isolado" o registro, mais atípico — maior prioridade de auditoria.',
          'Taxa de contaminação (parâmetro de entrada): a % esperada de registros anômalos na base — ajusta a sensibilidade do modelo.',
          'Não é prova de fraude: é um sinalizador estatístico para priorizar onde investigar, não uma conclusão automática.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'min_producao_procedimento', tipo: 'int', label: 'Produção Mínima do Procedimento', default: 30, obrigatorio: false },
          { nome: 'contaminacao', tipo: 'float', label: 'Contaminação Esperada', default: 0.02, obrigatorio: false },
          { nome: 'seed', tipo: 'int', label: 'Semente', default: 42, obrigatorio: false },
      ] },
    { key: 'hdbscan-estabelecimentos', title: 'HDBSCAN: Estabelecimentos Atípicos', grupo: 8,
      descricao: 'Encontra estabelecimentos que não se encaixam em nenhum cluster de perfil de produção.',
      sobre: 'HDBSCAN (clustering hierárquico baseado em densidade) agrupa estabelecimentos por perfil de produção ambulatorial (volume, diversidade de procedimentos, valor médio, % de alta complexidade). Diferente do K-Means, o HDBSCAN descobre sozinho o número de grupos e marca explicitamente como "ruído" (outlier) qualquer estabelecimento que não se encaixe bem em nenhum grupo denso — exatamente os mais atípicos da rede.',
      comoInterpretar: [
          'Estabelecimentos marcados como "ruído"/outlier: não se parecem com nenhum grupo — podem ser unidades altamente especializadas, mal cadastradas, ou com padrão fora do esperado para o seu porte.',
          'Clusters densos: grupos de estabelecimentos com perfil de produção semelhante — um "perfil típico" de unidade.',
          'O número de clusters é descoberto automaticamente pelo algoritmo, não definido manualmente.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'producao_minima', tipo: 'int', label: 'Produção Mínima', default: 100, obrigatorio: false },
          { nome: 'min_cluster_size', tipo: 'int', label: 'Tamanho Mínimo do Cluster', default: 5, obrigatorio: false },
      ] },

    { key: 'umap-perfis', title: 'UMAP+HDBSCAN: Perfis Municipais', grupo: 9,
      descricao: 'Projeta municípios em 2D (UMAP) e agrupa por perfil epidemiológico (HDBSCAN).',
      sobre: 'Reduz um painel de indicadores municipais (potencialmente dezenas de dimensões) para 2 dimensões usando UMAP (Uniform Manifold Approximation and Projection), preservando a estrutura de vizinhança dos dados originais, e agrupa os municípios projetados com HDBSCAN. Permite visualizar, num único mapa 2D, quais municípios têm perfil epidemiológico/socioeconômico semelhante.',
      comoInterpretar: [
          'Municípios próximos no mapa 2D: têm perfil parecido no conjunto completo de indicadores usados (não necessariamente próximos geograficamente).',
          'Cores/clusters: grupos de perfil descobertos pelo HDBSCAN.',
          'Pontos isolados fora de qualquer cluster: municípios com perfil atípico, sem par direto na base analisada.',
      ],
      campos: [
          { nome: 'painel_csv', tipo: 'file_csv', label: 'Painel de Indicadores (CSV)', default: null, obrigatorio: true },
          { nome: 'ufs', tipo: 'ufs', label: 'UFs (opcional)', default: [], obrigatorio: false },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'indicadores', tipo: 'texts', label: 'Indicadores (opcional)', default: [], obrigatorio: false },
          { nome: 'n_neighbors', tipo: 'int', label: 'n_neighbors (UMAP)', default: 15, obrigatorio: false },
          { nome: 'min_dist', tipo: 'float', label: 'min_dist (UMAP)', default: 0.1, obrigatorio: false },
          { nome: 'min_cluster_size', tipo: 'int', label: 'Tamanho Mínimo do Cluster', default: 5, obrigatorio: false },
          { nome: 'seed', tipo: 'int', label: 'Semente', default: 42, obrigatorio: false },
      ] },
    { key: 'analise-fatorial', title: 'Análise Fatorial: Indicadores de Saúde', grupo: 9,
      descricao: 'Reduz um painel de indicadores a poucos fatores latentes que explicam a variação conjunta.',
      sobre: 'Análise Fatorial (scikit-learn): busca um pequeno número de "fatores latentes" (não observados diretamente) que expliquem a variação conjunta de um painel de indicadores de saúde — por exemplo, vários indicadores de acesso a serviços podem, na prática, refletir um único fator subjacente de "infraestrutura de saúde municipal". Reduz a dimensionalidade preservando a informação compartilhada entre os indicadores correlacionados.',
      comoInterpretar: [
          'Cargas fatoriais: o quanto cada indicador original "pertence" a cada fator — cargas altas (positivas ou negativas) revelam quais indicadores formam aquele fator.',
          'Variância explicada por fator: quanto da variação total dos dados aquele fator captura sozinho.',
          'Um fator com cargas altas em indicadores de mortalidade infantil e pré-natal, por exemplo, pode ser interpretado como um eixo de "saúde materno-infantil".',
      ],
      campos: [
          { nome: 'painel_csv', tipo: 'file_csv', label: 'Painel de Indicadores (CSV)', default: null, obrigatorio: true },
          { nome: 'ufs', tipo: 'ufs', label: 'UFs (opcional)', default: [], obrigatorio: false },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'indicadores', tipo: 'texts', label: 'Indicadores (opcional)', default: [], obrigatorio: false },
          { nome: 'n_fatores', tipo: 'int_optional', label: 'Nº de Fatores (opcional)', default: null, obrigatorio: false },
      ] },

    { key: 'obito-materno', title: 'Triagem: Óbito Materno Mal Classificado', grupo: 10,
      descricao: 'Sinaliza óbitos de mulheres em idade fértil com suspeita de causa materna mal classificada.',
      sobre: 'Modelo de triagem que cruza óbitos de mulheres em idade fértil (SIM) com causas de óbito potencialmente relacionadas à gestação/puerpério, sinalizando casos com suspeita de subnotificação/má classificação de óbito materno — um problema conhecido de subnotificação nas estatísticas oficiais. Gera um score de suspeita, não um diagnóstico definitivo.',
      comoInterpretar: [
          'Score de suspeita mais alto: maior probabilidade de o óbito ser, na verdade, materno mas classificado incorretamente na causa básica — prioridade para revisão do prontuário/investigação de óbito.',
          'Limiar de suspeita (parâmetro de entrada): ajusta quantos casos são sinalizados — limiar mais baixo sinaliza mais casos (mais sensível, menos específico).',
          'É um apoio à vigilância epidemiológica, não substitui a investigação de óbito materno pela equipe de saúde.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022], obrigatorio: true },
          { nome: 'limiar_suspeita', tipo: 'float', label: 'Limiar de Suspeita (score)', default: 0.5, obrigatorio: false },
      ] },
    { key: 'sifilis-congenita', title: 'Determinantes: Sífilis Congênita', grupo: 10,
      descricao: 'Modela determinantes municipais da taxa de sífilis congênita.',
      sobre: 'Modela os determinantes municipais da taxa de sífilis congênita (SINAN), cruzando indicadores de cobertura de pré-natal e outros fatores socioeconômicos/de acesso, para identificar quais fatores mais se associam a taxas elevadas — informação que direciona políticas de eliminação da sífilis congênita, uma meta de saúde pública com metas explícitas de redução.',
      comoInterpretar: [
          'Municípios com taxa observada muito acima da esperada pelos determinantes: podem indicar falhas específicas na rede local (ex.: baixa testagem de parceiros) além do que os determinantes gerais explicam.',
          'Determinantes com maior associação: fatores mais fortemente ligados à taxa de sífilis congênita nesta amostra — candidatos a alvo de intervenção.',
          'Nascimentos mínimos por município (parâmetro): filtra municípios pequenos demais para uma taxa estável.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'min_nascimentos', tipo: 'int', label: 'Nascimentos Mínimos/Município', default: 30, obrigatorio: false },
      ] },
    { key: 'obito-neonatal', title: 'Óbito Neonatal: Precoce vs. Tardio', grupo: 10,
      descricao: 'Classifica o risco de óbito neonatal precoce (0-6 dias) vs. tardio (7-27 dias).',
      sobre: 'Classifica o risco de óbito neonatal diferenciando óbito precoce (0-6 dias de vida, tipicamente ligado a causas perinatais/obstétricas) de óbito tardio (7-27 dias, mais ligado a causas pós-natais/infecciosas) — a distinção importa porque as estratégias de prevenção são diferentes para cada janela.',
      comoInterpretar: [
          'Predominância de óbitos precoces: aponta para necessidade de reforço na assistência ao parto/pré-natal.',
          'Predominância de óbitos tardios: aponta para necessidade de reforço no acompanhamento pós-alta/puericultura precoce.',
          'Compare a distribuição entre municípios/estabelecimentos para identificar onde intervenções mais direcionadas fariam diferença.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
      ] },
    { key: 'uti-neonatal', title: 'Score: Demanda de UTI Neonatal', grupo: 10,
      descricao: 'Estima um score de demanda por vaga de UTI neonatal a partir de características do nascimento.',
      sobre: 'Estima um score de demanda por vaga de UTI neonatal a partir de características do nascimento (peso, idade gestacional, Apgar etc. do SINASC) — uma ferramenta de planejamento para antecipar a pressão sobre leitos de UTI neonatal a partir do perfil dos nascimentos observados, sem esperar pela ocupação real dos leitos.',
      comoInterpretar: [
          'Score mais alto: nascimento com maior probabilidade estimada de necessitar de UTI neonatal.',
          'Distribuição de scores por período/região: ajuda a planejar alocação de leitos com antecedência.',
          'O score é uma estimativa baseada em características ao nascer, não substitui a avaliação clínica do neonatologista.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
      ] },
    { key: 'robson', title: 'Classificação de Robson (Cesarianas)', grupo: 10,
      descricao: 'Classifica partos nos 10 grupos de Robson (OMS) para auditoria da taxa de cesáreas por hospital.',
      sobre: 'Classificação de Robson (recomendada pela OMS): agrupa todos os partos em 10 grupos mutuamente exclusivos, definidos por características obstétricas objetivas presentes no SINASC (paridade, tipo de gestação, apresentação fetal, idade gestacional, histórico de cesárea). É o padrão internacional para auditar taxas de cesárea de forma comparável entre hospitais, já que a taxa bruta não considera o perfil de risco da população atendida.',
      comoInterpretar: [
          'Taxa de cesárea por grupo de Robson: compara hospitais de forma justa, já que cada grupo tem risco obstétrico padronizado.',
          'Grupos 1 e 3 (nulíparas/multíparas, gestação única, cefálica, a termo, trabalho de parto espontâneo) com taxa de cesárea muito alta: sinal de possível cesárea sem indicação clínica clara.',
          'Contribuição de cada grupo para a taxa geral: mostra quais grupos mais pesam na taxa de cesárea total — prioriza onde investir esforço de redução.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'min_partos_hospital', tipo: 'int', label: 'Partos Mínimos p/ Hospital (auditoria)', default: 20, obrigatorio: false },
      ] },
    { key: 'kotelchuck', title: 'Índice de Kotelchuck (Pré-Natal)', grupo: 10,
      descricao: 'Classifica a adequação do pré-natal (APNCU) cruzando início e nº de consultas com a idade gestacional.',
      sobre: 'Índice de Kotelchuck (APNCU — Adequacy of Prenatal Care Utilization): classifica a adequação do pré-natal cruzando duas dimensões — quando o pré-natal começou (mês de início) e quantas consultas foram realizadas em relação ao número esperado para a idade gestacional no parto — em vez de olhar só o número de consultas isoladamente, como fazem a maioria dos indicadores tradicionais.',
      comoInterpretar: [
          'Adequado / Mais que Adequado: início precoce do pré-natal e número de consultas condizente (ou superior) ao esperado para a idade gestacional.',
          'Intermediário / Inadequado: início tardio e/ou número de consultas bem abaixo do esperado.',
          'Sem Pré-Natal: nenhuma consulta registrada.',
          'Compare desfechos perinatais (baixo peso, prematuridade) entre as categorias — normalmente pioram conforme a adequação diminui.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
      ] },
    { key: 'abandono-hanseniase', title: 'Risco de Abandono: Hanseníase', grupo: 10,
      descricao: 'Estima o risco de abandono do tratamento de hanseníase a partir do perfil do caso.',
      sobre: 'Estima o risco de abandono do tratamento de hanseníase a partir do perfil clínico e sociodemográfico do caso registrado no SINAN (forma clínica, grau de incapacidade, modo de detecção, esquema terapêutico etc.) — o abandono de tratamento é um dos principais obstáculos ao controle da hanseníase, pois favorece a manutenção da cadeia de transmissão e o desenvolvimento de incapacidades.',
      comoInterpretar: [
          'Score de risco de abandono mais alto: caso com maior probabilidade estimada de não concluir o tratamento — prioridade para busca ativa/acompanhamento reforçado.',
          'Fatores mais associados ao abandono: características do caso mais fortemente ligadas à interrupção do tratamento nesta amostra.',
          'É uma ferramenta de priorização para a vigilância, não uma decisão clínica automática.',
      ],
      campos: [
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2021, 2022, 2023], obrigatorio: false },
      ] },

    { key: 'fluxo-partos', title: 'Mapa de Fluxo de Partos', grupo: 5,
      descricao: 'Mapa de fluxo entre o município de residência da mãe e o município onde o parto ocorreu.',
      sobre: 'Mesma lógica do módulo "Fluxo de Pacientes" (SIH), aplicada ao SINASC: compara o município de RESIDÊNCIA da mãe com o município de OCORRÊNCIA do parto e desenha um mapa de fluxo — as linhas revelam quais municípios "exportam" gestantes para dar à luz em outro lugar (tipicamente por falta de maternidade/UTI neonatal local) e quais funcionam como polos de referência obstétrica.',
      comoInterpretar: [
          'Linhas mais grossas/claras (escala log): rotas com mais partos "exportados" — prioridade para investigar a causa (falta de leito obstétrico, UTI neonatal, risco gestacional).',
          'Municípios que só recebem linhas (nunca são origem): funcionam como polo de referência regional para partos.',
          'Municípios sem nenhuma linha: partos ocorrem majoritariamente no próprio município (sem fluxo relevante).',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022], obrigatorio: true },
          { nome: 'min_partos_fluxo', tipo: 'int', label: 'Mínimo de Partos por Rota', default: 5, obrigatorio: false },
      ] },
    { key: 'fluxo-alta-complexidade', title: 'Mapa de Fluxo de Alta Complexidade', grupo: 5,
      descricao: 'Mapa de fluxo entre o município de residência do paciente e o estabelecimento que realizou um procedimento de alta complexidade.',
      sobre: 'Mesma lógica do módulo "Fluxo de Pacientes", mas para procedimentos AMBULATORIAIS de alta complexidade (SIA/PA) — ex.: quimioterapia, radioterapia — em vez de internações (SIH). Compara o município de residência do paciente com o município do estabelecimento que realizou o procedimento, filtrado por prefixos de código SIGTAP. Revela quais municípios concentram a oferta desses serviços e de quão longe eles atraem pacientes.',
      comoInterpretar: [
          'Linhas mais grossas/claras (escala log): rotas com mais procedimentos realizados fora do município de residência.',
          'Municípios "polo" (só recebem linhas): concentram a oferta do procedimento selecionado na região.',
          'Ajuste os prefixos SIGTAP para outros procedimentos de alta complexidade (ex.: 0303 = radioterapia, 0501 = transplantes).',
      ],
      campos: [
          { nome: 'ufs', tipo: 'ufs', label: 'UFs', default: ['TO'], obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022], obrigatorio: true },
          { nome: 'proc_prefixos', tipo: 'texts', label: 'Prefixos SIGTAP do Procedimento', default: ['0304'], obrigatorio: false },
          { nome: 'min_procedimentos_fluxo', tipo: 'int', label: 'Mínimo de Procedimentos por Rota', default: 5, obrigatorio: false },
      ] },
    { key: 'difusao-espacial-surto', title: 'Difusão Espacial de Surto', grupo: 1,
      descricao: 'Sequência de mapas mensais mostrando como um agravo se espalhou geograficamente ao longo do tempo.',
      sobre: 'Diferente dos mapas de fluxo (origem→destino) e dos mapas de autocorrelação espacial (um único retrato estático), este modelo mostra COMO um agravo se espalhou geograficamente mês a mês: agrega as notificações do SINAN por município e mês, e desenha uma grade de mapas coropléticos (pequenos múltiplos) na mesma escala de cor, um por mês, para visualizar a progressão espacial da epidemia. Também gera uma série temporal com os municípios mais afetados.',
      comoInterpretar: [
          'Cada painel do mapa é um mês — observe quais municípios "acendem" (ficam mais escuros) primeiro e como a mancha se espalha para os vizinhos ao longo dos painéis.',
          'Todos os painéis usam a MESMA escala de cor, então a intensidade é comparável entre meses.',
          'O gráfico de linhas (Plotly) mostra a evolução mensal de casos dos municípios mais afetados — útil para ver se o pico foi simultâneo ou defasado entre eles.',
      ],
      campos: [
          { nome: 'dis_code', tipo: 'text', label: 'Código do Agravo (SINAN)', default: 'DENG', obrigatorio: false },
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'anos', tipo: 'anos', label: 'Anos', default: [2022], obrigatorio: true },
          { nome: 'max_paineis', tipo: 'int', label: 'Máximo de Meses (painéis)', default: 6, obrigatorio: false },
      ] },
    { key: 'desertos-assistenciais', title: 'Mapa de Desertos Assistenciais', grupo: 1,
      descricao: 'Distância de cada município ao estabelecimento de saúde de um tipo específico mais próximo (CNES).',
      sobre: 'Para um tipo de estabelecimento escolhido (TP_UNID do CNES — ex.: Hospital Geral, Hospital Especializado), identifica quais municípios da UF possuem pelo menos uma unidade desse tipo e calcula, para TODOS os municípios (inclusive os que já têm o recurso, com distância zero), a distância em linha reta até o município mais próximo que o possui. Municípios "desertos" — longe de qualquer unidade do tipo escolhido — aparecem destacados no mapa.',
      comoInterpretar: [
          'Municípios mais escuros no mapa: mais distantes de qualquer estabelecimento do tipo selecionado — candidatos a "deserto assistencial" para esse recurso.',
          'Distância = 0: o próprio município já possui ao menos um estabelecimento do tipo escolhido.',
          'Troque os tipos de unidade (TP_UNID) para investigar outros recursos — ex.: 02 = UBS, 05 = Hospital Geral, 07 = Hospital Especializado.',
      ],
      campos: [
          { nome: 'uf', tipo: 'uf', label: 'UF', default: 'TO', obrigatorio: true },
          { nome: 'ano', tipo: 'ano', label: 'Ano', default: 2022, obrigatorio: true },
          { nome: 'tipos_unidade', tipo: 'texts', label: 'Tipos de Unidade CNES (TP_UNID)', default: ['05', '07'], obrigatorio: false },
      ] },
];

export const getModelagemSpec = (key) => MODELAGEM_AVANCADA_SPEC.find(m => m.key === key) || null;

export const getModelagemGroupsOrdered = () => {
    const porGrupo = {};
    MODELAGEM_AVANCADA_SPEC.forEach(m => {
        if (!porGrupo[m.grupo]) porGrupo[m.grupo] = [];
        porGrupo[m.grupo].push(m);
    });
    return Object.keys(porGrupo)
        .map(Number)
        .sort((a, b) => a - b)
        .map(grupo => ({ grupo, ...GRUPOS_MODELAGEM[grupo], modelos: porGrupo[grupo] }));
};
