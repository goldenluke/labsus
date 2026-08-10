// Catálogo único de todas as pipelines de análise do LabSUS (as históricas,
// as de BPHO/PopulationSpace e os 30 modelos de Modelagem Avançada).
//
// Existia antes uma separação artificial entre "pipelines antigas" e
// "Modelagem Avançada" — essa separação refletia apenas a ordem em que as
// coisas foram construídas, não uma diferença real para quem usa o sistema.
// Aqui todas são classificadas por UMA taxonomia baseada na técnica/domínio
// metodológico, e tanto a Sidebar quanto a HomePage renderizam a partir
// deste único catálogo — garantindo que as duas superfícies fiquem sempre
// consistentes entre si.
import {
    FiDatabase, FiGrid, FiGlobe, FiPieChart, FiTrendingUp, FiWatch, FiShare2,
    FiGitMerge, FiMessageSquare, FiAlertOctagon, FiLayers, FiTarget, FiShield,

    FiBarChart2, FiMap, FiGitPullRequest, FiUserCheck, FiCrosshair, FiDollarSign,
    FiAlertTriangle, FiClock, FiThermometer, FiSmile, FiClipboard,
    FiCpu, FiBookOpen, FiEye, FiHexagon, FiGitCommit, FiGitBranch, FiActivity,
    FiZap, FiBox, FiCompass, FiFlag, FiFileText, FiUsers, FiRepeat,
    FiTrendingDown, FiBell, FiAnchor, FiSliders,

    FiMapPin, FiSun, FiLink2, FiScissors, FiBarChart, FiWind, FiCornerUpRight, FiPlusSquare,
    FiCalendar, FiRotateCcw, FiColumns, FiDivideSquare, FiMessageCircle, FiOctagon, FiXCircle,
    FiLayout, FiAlertCircle, FiUserPlus, FiUser, FiPower, FiList, FiCheckSquare, FiUserMinus,
} from 'react-icons/fi';

import { MODELAGEM_AVANCADA_SPEC } from './modelagemAvancadaSpec';
import { INDICES_COMPOSTOS_SPEC } from './indicesCompostosSpec';

// Uma cor por categoria (não por item) — reforça visualmente a que família
// metodológica cada pipeline pertence, tanto na Home quanto (futuramente) na Sidebar.
export const CATEGORIAS = [
    { id: 'integracao-dados', label: 'Integração & Engenharia de Dados', icon: FiDatabase, color: 'cyan',
      descricao: 'Consolidação de bases brutas do DATASUS em painéis prontos para análise.' },
    { id: 'perfis-representacao', label: 'Perfis & Representação', icon: FiGrid, color: 'blue',
      descricao: 'Vetorização e agrupamento de territórios, estabelecimentos e outras unidades de análise.' },
    { id: 'risco-triagem', label: 'Risco Individual & Triagem Clínica', icon: FiTarget, color: 'emerald',
      descricao: 'Classificação e escore de risco para pacientes, partos e casos individuais.' },
    { id: 'series-temporais', label: 'Séries Temporais & Alerta Precoce', icon: FiTrendingUp, color: 'orange',
      descricao: 'Sazonalidade, quebras estruturais, excesso de eventos e sinais precoces de mudança.' },
    { id: 'sobrevivencia', label: 'Sobrevivência & Tempo-ao-Evento', icon: FiWatch, color: 'rose',
      descricao: 'Kaplan-Meier e Cox para tempo até alta, óbito, reincidência ou abandono.' },
    { id: 'analise-espacial', label: 'Análise Espacial', icon: FiGlobe, color: 'teal',
      descricao: 'Autocorrelação e clusters geográficos (Moran, LISA, Getis-Ord).' },
    { id: 'bayesiano-glm', label: 'Bayesiano & Modelos Lineares Generalizados', icon: FiPieChart, color: 'indigo',
      descricao: 'Estimação bayesiana de pequenas áreas e regressões para dados de contagem.' },
    { id: 'redes-grafos', label: 'Redes & Grafos', icon: FiShare2, color: 'purple',
      descricao: 'Coocorrência, similaridade e propagação sobre grafos de comorbidades e estabelecimentos.' },
    { id: 'inferencia-causal', label: 'Inferência Causal', icon: FiGitMerge, color: 'slate',
      descricao: 'Diferenças-em-diferenças, descontinuidade de regressão e simulação contrafactual.' },
    { id: 'anomalias', label: 'Detecção de Anomalias', icon: FiAlertOctagon, color: 'red',
      descricao: 'Isolation Forest e HDBSCAN para outliers de produção, custo e estabelecimento.' },
    { id: 'dimensionalidade', label: 'Redução de Dimensionalidade', icon: FiLayers, color: 'amber',
      descricao: 'UMAP, Análise Fatorial e topologia para simplificar indicadores correlacionados.' },
    { id: 'vigilancia-ontologia', label: 'Vigilância & Ontologia (BPHO)', icon: FiShield, color: 'green',
      descricao: 'Consulta direta a dados brutos e estruturais da ontologia — não são modelos estatísticos.' },
    // Por último, de propósito: técnicas exploratórias (hoje, NLP sobre texto
    // livre) com menor apelo clínico imediato que as demais categorias.
    { id: 'modulos-experimentais', label: 'Módulos Experimentais', icon: FiCpu, color: 'pink',
      descricao: 'Técnicas exploratórias, ainda sem validação clínica consolidada.' },
    // Índices de 2ª camada: compõem os indicadores acima (não aparecem na
    // pipeline de Integração de Indicadores — têm dashboard dedicado).
    { id: 'indices-compostos', label: 'Índices Compostos', icon: FiActivity, color: 'indigo',
      descricao: 'Índices de 2ª camada que combinam vários indicadores num único score — cada um com seu próprio dashboard (radar, ranking, mapa, tendência).' },
];

const GRUPO_MODELAGEM_PARA_CATEGORIA = {
    1: 'analise-espacial',
    2: 'bayesiano-glm',
    3: 'series-temporais',
    4: 'sobrevivencia',
    5: 'redes-grafos',
    6: 'inferencia-causal',
    7: 'modulos-experimentais',
    8: 'anomalias',
    9: 'dimensionalidade',
    10: 'risco-triagem',
};

const ICONE_MODELAGEM_AVANCADA = {
    'moran-mortalidade': FiGlobe,
    'lisa-sinan': FiMapPin,
    'hotspots-internacao': FiSun,
    'moran-bivariado': FiLink2,
    'gerar-painel-geografico': FiMap,
    'bayes-pequenas-areas': FiPieChart,
    'changepoint-bayesiano': FiScissors,
    'binomial-negativa': FiBarChart,
    'stl-sarima-arboviroses': FiWind,
    'quebra-estrutural': FiCornerUpRight,
    'excesso-mortalidade': FiPlusSquare,
    'sobrevida-tb': FiWatch,
    'sobrevida-permanencia': FiCalendar,
    'sobrevida-reincidencia': FiRotateCcw,
    'rede-comorbidades': FiShare2,
    'rede-especializacao': FiGitMerge,
    'diff-in-diff': FiColumns,
    'rdd-peso-nascer': FiDivideSquare,
    'gravidade-texto': FiMessageSquare,
    'similaridade-relatos': FiMessageCircle,
    'isolation-forest': FiOctagon,
    'hdbscan-estabelecimentos': FiXCircle,
    'umap-perfis': FiLayout,
    'analise-fatorial': FiLayers,
    'obito-materno': FiAlertCircle,
    'sifilis-congenita': FiUserPlus,
    'obito-neonatal': FiUser,
    'uti-neonatal': FiPower,
    'robson': FiList,
    'kotelchuck': FiCheckSquare,
    'abandono-hanseniase': FiUserMinus,
    'previsao-obitos': FiTrendingDown,
    'previsao-nascimentos': FiSmile,
    'previsao-producao-ambulatorial': FiBarChart2,
};

const pipelinesModelagemAvancada = MODELAGEM_AVANCADA_SPEC.filter((modelo) => !modelo.oculto).map((modelo) => ({
    key: modelo.key,
    path: `/pipelines/modelagem/${modelo.key}`,
    title: modelo.title,
    descricao: modelo.descricao,
    icon: ICONE_MODELAGEM_AVANCADA[modelo.key] || FiBox,
    categoria: GRUPO_MODELAGEM_PARA_CATEGORIA[modelo.grupo],
    bpho: false,
}));

// Índices compostos (src/indices/) — um único dashboard genérico por índice
// (/dashboards/indices/<key>), não a dupla pipelines+dashboards das demais
// famílias: o disparo (UFs/anos) e o resultado vivem na mesma página.
const pipelinesIndicesCompostos = INDICES_COMPOSTOS_SPEC.map((indice) => ({
    key: indice.key,
    path: `/dashboards/indices/${indice.key}`,
    title: `${indice.sigla} — ${indice.titulo}`,
    descricao: indice.descricao,
    icon: FiActivity,
    categoria: 'indices-compostos',
    bpho: false,
}));

// Pipelines já existentes antes da Modelagem Avançada (históricas + BPHO),
// agora reclassificadas na mesma taxonomia acima em vez de ficarem soltas
// em "Engenharia e População" / "Inteligência Preditiva" / grupos BPHO.
const pipelinesHistoricas = [
    { key: 'indicadores', path: '/pipelines/indicadores', title: 'Integração de Indicadores',
      descricao: 'Consolide dados do SIM, SIH, SIA, SINASC, SINAN, CNES e IBGE em um painel único.',
      icon: FiBarChart2, categoria: 'integracao-dados', bpho: false },
    { key: 'fluxo-pacientes', path: '/pipelines/fluxo-pacientes', title: 'Fluxo de Pacientes',
      descricao: 'Mapeie o deslocamento de pacientes entre municípios de residência e atendimento.',
      icon: FiGitPullRequest, categoria: 'integracao-dados', bpho: false },

    { key: 'kmeans', path: '/pipelines/kmeans', title: 'Perfis de Saúde (K-Means)',
      descricao: 'Agrupe territórios por semelhança epidemiológica e socioeconômica.',
      icon: FiMap, categoria: 'perfis-representacao', bpho: false },
    { key: 'population-space', path: '/pipelines/population-space', title: 'PopulationSpace',
      descricao: 'Vetorize estabelecimentos de saúde em um espaço de representação (BioSpace) a partir de utilização, força de trabalho e demografia, e agrupe por semelhança (KMeans).',
      icon: FiGrid, categoria: 'perfis-representacao', bpho: true },
    { key: 'population-compare', path: '/pipelines/population-compare', title: 'Comparar Estabelecimentos',
      descricao: 'Meça a distância entre estabelecimentos no espaço de representação completo (12 dimensões) — euclidiana, Mahalanobis, cosine ou DTW.',
      icon: FiGitMerge, categoria: 'perfis-representacao', bpho: true },
    { key: 'population-per-capita', path: '/pipelines/population-per-capita', title: 'Per Capita (Taxa Populacional)',
      descricao: 'Divide as contagens do estabelecimento pela população do município (mesma escala do pipeline de Indicadores) — auditável, sem modelo ajustado.',
      icon: FiCompass, categoria: 'perfis-representacao', bpho: true },
    { key: 'population-municipio', path: '/pipelines/population-municipio', title: 'Município',
      descricao: 'Trata um município (não um estabelecimento) como unidade de análise, cruzando SIH, SIM, SINASC e SINAN do mesmo território ao longo do tempo.',
      icon: FiFlag, categoria: 'perfis-representacao', bpho: true },
    { key: 'population-notificacao', path: '/pipelines/population-notificacao', title: 'Caso de Notificação',
      descricao: 'Trata uma notificação do SINAN (não o paciente, não o estabelecimento) como unidade de análise, do perfil na entrada até o desfecho no encerramento.',
      icon: FiFileText, categoria: 'perfis-representacao', bpho: true },
    { key: 'population-familia', path: '/pipelines/population-familia', title: 'Família',
      descricao: 'Trata uma família do CadÚnico (não o paciente, não o domicílio) como unidade de análise, consultando composição estrutural em tempo real contra a BPHO.',
      icon: FiUsers, categoria: 'perfis-representacao', bpho: true },

    { key: 'risco-readmissao', path: '/pipelines/risco-readmissao', title: 'Risco de Readmissão',
      descricao: 'Avalie a probabilidade de um paciente retornar ao hospital em 30 dias.',
      icon: FiUserCheck, categoria: 'risco-triagem', bpho: false },
    { key: 'custo-internacao', path: '/pipelines/custo-internacao', title: 'Previsão de Custo de Internação',
      descricao: 'Estime o custo individual da internação com base em características do paciente e do procedimento.',
      icon: FiDollarSign, categoria: 'risco-triagem', bpho: false },
    { key: 'risco-perinatal', path: '/pipelines/risco-perinatal', title: 'Risco Perinatal',
      descricao: 'Classifique o risco de complicações perinatais para recém-nascidos com base em dados do SINASC.',
      icon: FiThermometer, categoria: 'risco-triagem', bpho: false },
    { key: 'doencas-cronicas', path: '/pipelines/doencas-cronicas', title: 'Doenças Crônicas',
      descricao: 'Identifique a coorte de pacientes crônicos com risco de hospitalização em 6 meses.',
      icon: FiClipboard, categoria: 'risco-triagem', bpho: false },
    { key: 'regressao-obitos', path: '/pipelines/regressao-obitos', title: 'Regressão de Risco de Óbito',
      descricao: 'Identifique fatores críticos que influenciam a mortalidade em grupos específicos.',
      icon: FiCrosshair, categoria: 'bayesiano-glm', bpho: false },
    { key: 'population-risk', path: '/pipelines/population-risk', title: 'Score de Risco',
      descricao: 'Soma ponderada e auditável (não um modelo treinado) para rankear estabelecimentos por risco.',
      icon: FiTarget, categoria: 'risco-triagem', bpho: true },
    { key: 'population-uncertainty', path: '/pipelines/population-uncertainty', title: 'Previsão com Incerteza',
      descricao: 'Processo Gaussiano prevê um indicador de utilização com uma faixa de incerteza por estabelecimento.',
      icon: FiZap, categoria: 'risco-triagem', bpho: true },
    { key: 'population-classify', path: '/pipelines/population-classify', title: 'Classificador + SHAP',
      descricao: 'RandomForest separa hospitais acima/abaixo de um indicador e explica cada previsão por SHAP.',
      icon: FiBox, categoria: 'risco-triagem', bpho: true },

    { key: 'predicao-internacoes', path: '/pipelines/predicao-internacoes', title: 'Previsão de Internações',
      descricao: 'Projete a demanda hospitalar futura utilizando séries temporais.',
      icon: FiTrendingUp, categoria: 'series-temporais', bpho: false },
    { key: 'deteccao-surtos', path: '/pipelines/deteccao-surtos', title: 'Detecção de Surtos Epidemiológicos',
      descricao: 'Identifique anomalias e picos atípicos na ocorrência de doenças por território e CID.',
      icon: FiAlertTriangle, categoria: 'series-temporais', bpho: false },
    { key: 'population-early-warning', path: '/pipelines/population-early-warning', title: 'Alerta Precoce',
      descricao: 'Critical slowing down (variância + autocorrelação + assimetria crescentes) na trajetória de cada estabelecimento, com significância por substitutos AR(1).',
      icon: FiBell, categoria: 'series-temporais', bpho: true },
    { key: 'population-dynamics', path: '/pipelines/population-dynamics', title: 'Dinâmica & Estabilidade',
      descricao: 'Reversão à média (Ornstein-Uhlenbeck) por indicador, agrupada sobre toda a população — quais dos 12 eixos são estruturalmente estáveis vs. divergentes.',
      icon: FiAnchor, categoria: 'series-temporais', bpho: true },
    { key: 'population-transitions', path: '/pipelines/population-transitions', title: 'Transições de Fenótipo',
      descricao: 'Meça a probabilidade de transição entre fenótipos (KMeans) e o tempo real decorrido ao longo das competências.',
      icon: FiRepeat, categoria: 'series-temporais', bpho: true },

    { key: 'los-hibrido', path: '/pipelines/los-hibrido', title: 'LOS Híbrido (Tempo de Permanência)',
      descricao: 'Classifique e preveja a duração da internação (curta vs. longa permanência) por departamento.',
      icon: FiClock, categoria: 'sobrevivencia', bpho: false },
    { key: 'sobrevida-infantil', path: '/pipelines/sobrevida-infantil', title: 'Sobrevida Infantil',
      descricao: 'Preveja a probabilidade de óbito infantil com base em características do parto e da mãe.',
      icon: FiSmile, categoria: 'sobrevivencia', bpho: false },
    { key: 'population-survival', path: '/pipelines/population-survival', title: 'Sobrevida (Fenótipo)',
      descricao: 'Kaplan-Meier + Cox sobre o tempo até a composição demográfica dos internados cruzar um limiar, estratificado por fenótipo.',
      icon: FiTrendingDown, categoria: 'sobrevivencia', bpho: true },

    { key: 'population-graph', path: '/pipelines/population-graph', title: 'Grafo de Similaridade',
      descricao: 'Rede de vizinhos mais próximos entre estabelecimentos, com detecção de comunidades (Louvain).',
      icon: FiHexagon, categoria: 'redes-grafos', bpho: true },
    { key: 'population-gnn', path: '/pipelines/population-gnn', title: 'GNN (Classificação de Nós)',
      descricao: 'Graph Convolutional Network propaga o fenótipo (KMeans) pelo grafo de similaridade — semi-supervisionado e transdutivo (Kipf & Welling, 2017).',
      icon: FiGitBranch, categoria: 'redes-grafos', bpho: true },

    { key: 'population-causal', path: '/pipelines/population-causal', title: 'Causal (Densidade x LOS)',
      descricao: 'Pareamento por escore de propensão entre hospitais de alta e baixa densidade de vínculos/internação.',
      icon: FiActivity, categoria: 'inferencia-causal', bpho: true },
    { key: 'population-intervene', path: '/pipelines/population-intervene', title: 'Intervenção (Contrafactual)',
      descricao: 'Simule "e se": desloque uma Feature de um estabelecimento e veja o efeito no Score de Risco e na probabilidade do Classificador já treinados.',
      icon: FiSliders, categoria: 'inferencia-causal', bpho: true },

    { key: 'population-anomaly', path: '/pipelines/population-anomaly', title: 'Anomalias (Hospitais)',
      descricao: 'Sinalize hospitais estatisticamente atípicos frente ao grupo selecionado (IsolationForest).',
      icon: FiAlertOctagon, categoria: 'anomalias', bpho: true },

    { key: 'population-factor', path: '/pipelines/population-factor', title: 'Fatores Latentes',
      descricao: 'Análise Fatorial: reduz as 12 Features a poucos eixos de variação compartilhada entre os estabelecimentos.',
      icon: FiLayers, categoria: 'dimensionalidade', bpho: true },
    { key: 'population-topology', path: '/pipelines/population-topology', title: 'Topologia',
      descricao: 'Homologia persistente (Betti numbers) + grafo Mapper — o formato não-linear da população de estabelecimentos.',
      icon: FiGitCommit, categoria: 'dimensionalidade', bpho: true },

    { key: 'hospitalizacao-rdf', path: '/pipelines/hospitalizacao-rdf', title: 'Hospitalização (BPHO)',
      descricao: 'Carrega uma competência do SIH na ontologia (BPHO) e agrega hospitalizações por estabelecimento via SPARQL.',
      icon: FiShare2, categoria: 'vigilancia-ontologia', bpho: true },
    { key: 'chat-bpho', path: '/pipelines/chat-bpho', title: 'Chat com a BPHO',
      descricao: 'Pergunte em português sobre os dados e conceitos da ontologia — roda inteiramente local (Qwen3-Coder via Ollama).',
      icon: FiCpu, categoria: 'vigilancia-ontologia', bpho: true },
    { key: 'cnes-validity', path: '/pipelines/cnes-validity', title: 'Qualificações CNES',
      descricao: 'Habilitações, metas, incentivos e status regulatórios de um estabelecimento, direto da BPHO.',
      icon: FiShield, categoria: 'vigilancia-ontologia', bpho: true },
    { key: 'registros-vitais', path: '/pipelines/registros-vitais', title: 'Registros Vitais',
      descricao: 'Nascimentos e óbitos reais (SINASC/SIM), direto da BPHO.',
      icon: FiBookOpen, categoria: 'vigilancia-ontologia', bpho: true },
    { key: 'sinan-vigilancia', path: '/pipelines/sinan-vigilancia', title: 'Vigilância SINAN',
      descricao: '48 das 49 bases (agravos) reais do SINAN, direto da BPHO — busca por agravo e desfecho de caso.',
      icon: FiEye, categoria: 'vigilancia-ontologia', bpho: true },
];

export const PIPELINES = [...pipelinesHistoricas, ...pipelinesModelagemAvancada, ...pipelinesIndicesCompostos];

// Retorna as categorias na ordem de exibição, cada uma já filtrada pelo
// acesso do usuário e com suas pipelines — pronto para renderizar tanto na
// Sidebar quanto na HomePage sem duplicar a lógica de classificação/filtro.
export const getCatalogoPorCategoria = (hasBphoAccess) => {
    return CATEGORIAS
        .map((categoria) => ({
            ...categoria,
            pipelines: PIPELINES.filter((p) => p.categoria === categoria.id && (!p.bpho || hasBphoAccess)),
        }))
        .filter((categoria) => categoria.pipelines.length > 0);
};
