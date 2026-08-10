// Metadados dos 10 índices compostos de 2ª camada (src/indices/) — cada um
// é calculado sob demanda via /api/pipelines/indices-compostos/trigger/
// (um único endpoint genérico, parametrizado por `indice`) e renderizado
// pelo mesmo dashboard genérico (IndiceCompostoDashboardPage.jsx).
//
// `componentes` lista as colunas do CSV usadas no radar de decomposição —
// os nomes batem exatamente com as colunas emitidas por cada
// src/indices/<key>.py (já com o sufixo _<SIGLA> para evitar colisão).
export const INDICES_COMPOSTOS_SPEC = [
    {
        key: 'hsri', titulo: 'Healthcare Structural Robustness Index', sigla: 'HSRI', grupo: 'Equilíbrio Estrutural',
        descricao: 'Equilíbrio entre capacidade instalada, pressão de demanda e mortalidade hospitalar num único ponto no tempo — não mede resposta a um choque (resiliência em sentido estrito), e sim robustez estrutural.',
        formula: 'Capacidade / (1 + 0,5×Demanda + 0,5×Mortalidade), reescalado por uma curva logística fixa (razão=1 → score=50)',
        colunaScore: 'HSRI',
        componentes: [
            { coluna: 'CAPACIDADE_HSRI', label: 'Capacidade' },
            { coluna: 'DEMANDA_HSRI', label: 'Demanda' },
            { coluna: 'MORTALIDADE_HSRI', label: 'Mortalidade (hospitalar ajustada)' },
        ],
        interpretacao: 'Score mais alto = mais capacidade instalada frente à demanda e à mortalidade hospitalar observadas, num único ponto no tempo. Não é uma medida de resiliência dinâmica (capacidade de se recuperar de um choque) — dois municípios com a mesma capacidade podem ter score bem diferente mesmo que o de demanda mais alta absorva proporcionalmente mais pacientes com a mesma mortalidade. Municípios pequenos sem hospital local podem aparecer artificialmente altos (poucos casos, taxas per capita instáveis) — compare com o Índice de Capacidade Assistencial bruto antes de tirar conclusões.',
    },
    {
        key: 'hnfi', titulo: 'Healthcare Network Fragmentation Index', sigla: 'HNFI', grupo: 'Rede',
        descricao: 'O quanto a rede assistencial usada pelos residentes está espalhada entre muitos estabelecimentos/municípios diferentes, em vez de concentrada num polo de referência.',
        colunaScore: 'HNFI',
        componentes: [
            { coluna: 'N_ESTABELECIMENTOS_DISTINTOS_HNFI', label: 'Nº Estabelecimentos' },
            { coluna: 'SHANNON_DIVERSIDADE_HOSPITAIS_HNFI', label: 'Diversidade de Hospitais' },
            { coluna: 'RIQUEZA_DESTINOS_HNFI', label: 'Municípios de Destino' },
        ],
        interpretacao: 'Score mais alto = rede mais fragmentada (residentes usam muitos provedores diferentes). Score baixo = atendimento concentrado, tipicamente no próprio município ou num único polo regional.',
    },
    {
        key: 'meci', titulo: 'Municipal Epidemiological Complexity Index', sigla: 'MECI', grupo: 'Complexidade',
        descricao: 'Diversidade da carga de doenças e da produção assistencial de um município — óbitos, internações, procedimentos e tipos de estabelecimento.',
        colunaScore: 'MECI',
        componentes: [
            { coluna: 'SHANNON_DIVERSIDADE_OBITOS_MECI', label: 'Diversidade de Óbitos' },
            { coluna: 'SHANNON_DIVERSIDADE_INTERNACOES_MECI', label: 'Diversidade de Internações' },
            { coluna: 'N_PROC_DISTINTOS_HOSP_MECI', label: 'Procedimentos Distintos' },
            { coluna: 'SHANNON_DIVERSIDADE_ASSISTENCIAL_MECI', label: 'Diversidade Assistencial' },
        ],
        interpretacao: 'Score mais alto = carga epidemiológica e produção assistencial espalhadas por muitas causas/procedimentos diferentes, não concentradas num pequeno número delas.',
    },
    {
        key: 'cci', titulo: 'Continuity of Care Index', sigla: 'CCI', grupo: 'Continuidade',
        descricao: 'Proxy agregado (sem linkage individual) de continuidade do cuidado: uso do ambulatório para resolver antes de precisar de internação, e desfecho favorável quando ela ocorre.',
        colunaScore: 'CCI',
        componentes: [
            { coluna: 'RAZAO_AMBULATORIAL_HOSPITALAR_CCI', label: 'Razão Ambulatorial/Hospitalar' },
            { coluna: 'IND_RESOLUTIVIDADE_CCI', label: 'Resolutividade Hospitalar' },
        ],
        interpretacao: 'Score mais alto = mais resolução na atenção ambulatorial (menos dependência só do hospital) e melhor desfecho quando a internação acontece. Não captura retorno pós-alta nem desfecho por paciente — é um proxy estrutural, não uma medida de continuidade individual.',
    },
    {
        key: 'hae', titulo: 'Healthcare Flow Entropy', sigla: 'HAE', grupo: 'Rede',
        descricao: 'Dispersão do fluxo assistencial (SIH+SIA combinados) usado pelos residentes de um município — mede fragmentação/regionalização da rede, não acesso em si.',
        colunaScore: 'HAE',
        componentes: [
            { coluna: 'SHANNON_ENTROPIA_ACESSO_HAE', label: 'Entropia do Fluxo' },
            { coluna: 'SIMPSON_DIVERSIDADE_ACESSO_HAE', label: 'Diversidade (Simpson)' },
            { coluna: 'RIQUEZA_DESTINOS_HAE', label: 'Municípios de Destino' },
            { coluna: 'P_LOCAL_HAE', label: '% Atendido no Próprio Município' },
            { coluna: 'MAX_PI_HAE', label: '% no Destino Dominante' },
        ],
        interpretacao: 'Entropia alta = os residentes se atendem em muitos municípios diferentes; baixa = atendimento concentrado (geralmente no próprio município ou num único polo). Atenção: entropia alta não significa necessariamente melhor acesso — pode indicar peregrinação do paciente e falta de referência definida em vez de rede regionalizada. Cheque P_LOCAL e MAX_PI_HAE para diferenciar os dois cenários, e desconsidere o score de municípios com AMOSTRA_PEQUENA_HAE=true (menos de 30 eventos, entropia estatisticamente instável).',
    },
    {
        key: 'hvs', titulo: 'Healthcare Vulnerability Score', sigla: 'HVS', grupo: 'Vulnerabilidade',
        descricao: 'Vulnerabilidade estrutural: baixa capacidade instalada combinada com alta pressão evitável (ICSAP) e alta mortalidade evitável (TMI).',
        colunaScore: 'HVS',
        componentes: [
            { coluna: 'INVERSO_CAPACIDADE_HVS', label: 'Falta de Capacidade' },
            { coluna: 'DOENCAS_CRONICAS_HVS', label: 'Internações ICSAP' },
            { coluna: 'TMI_HVS', label: 'Mortalidade Infantil' },
        ],
        interpretacao: 'Score mais alto = município estruturalmente mais vulnerável (pouca capacidade instalada + alta pressão evitável sobre o sistema). Prioridade para investimento em atenção primária.',
    },
    {
        key: 'teri', titulo: 'Territorial Epidemiological Resilience Index', sigla: 'TERI', grupo: 'Resiliência',
        descricao: 'Capacidade de um território voltar ao patamar basal depois de um pico de utilização/mortalidade — requer uma série de vários anos.',
        colunaScore: 'TERI',
        requerVariosAnos: true,
        anosMinimosRecomendados: 5,
        componentes: [
            { coluna: 'VELOCIDADE_RECUPERACAO_INTERNACOES_TERI', label: 'Velocidade Recup. (Internações)' },
            { coluna: 'VELOCIDADE_RECUPERACAO_MORTALIDADE_TERI', label: 'Velocidade Recup. (Mortalidade)' },
            { coluna: 'IND_CAPACIDADE_ASSISTENCIAL_TERI', label: 'Capacidade Instalada' },
        ],
        interpretacao: 'Score mais alto = território com mais capacidade instalada E recuperação mais rápida depois de um pico. Com poucos anos de dados, o pico/recuperação pode não ter sido observado dentro da janela — resultado fica menos confiável.',
    },
    {
        key: 'phsi', titulo: 'Population Health Stability Index', sigla: 'PHSI', grupo: 'Estabilidade',
        descricao: 'Estabilidade dinâmica da saúde populacional ao longo do tempo — variância, autocorrelação (critical slowing down), curtose e coeficiente de variação das séries de internação e mortalidade. Requer uma série de vários anos.',
        colunaScore: 'PHSI',
        requerVariosAnos: true,
        anosMinimosRecomendados: 5,
        componentes: [
            { coluna: 'VARIANCIA_INTERNACOES_PHSI', label: 'Variância (Internações)' },
            { coluna: 'AUTOCORR_LAG1_INTERNACOES_PHSI', label: 'Autocorrelação (Internações)' },
            { coluna: 'CV_INTERNACOES_PHSI', label: 'Coef. Variação (Internações)' },
            { coluna: 'VARIANCIA_MORTALIDADE_PHSI', label: 'Variância (Mortalidade)' },
            { coluna: 'AUTOCORR_LAG1_MORTALIDADE_PHSI', label: 'Autocorrelação (Mortalidade)' },
            { coluna: 'CV_MORTALIDADE_PHSI', label: 'Coef. Variação (Mortalidade)' },
        ],
        interpretacao: 'Score mais alto = série mais estável (o índice já inverte os componentes brutos, que são medidas de instabilidade). Autocorrelação lag-1 alta é um sinal precoce clássico de "critical slowing down" — a série demora mais para voltar ao equilíbrio depois de um choque, possível aviso de transição crítica à frente.',
    },
    {
        key: 'hssi', titulo: 'Healthcare System Stress Index', sigla: 'HSSI', grupo: 'Pressão',
        descricao: 'Sobrecarga da rede hospitalar local — ocupação, permanência, gravidade e complexidade simultâneas sobre a capacidade instalada.',
        colunaScore: 'HSSI',
        componentes: [
            { coluna: 'IND_PRESSAO_LEITOS_HSSI', label: 'Pressão sobre Leitos' },
            { coluna: 'IND_PRESSAO_PERMANENCIA_HSSI', label: 'Pressão de Permanência' },
            { coluna: 'TMH_HOSPITALAR_HSSI', label: 'Mortalidade Hospitalar' },
            { coluna: 'IND_COMPLEXIDADE_HOSPITALAR_HSSI', label: 'Complexidade Hospitalar' },
        ],
        interpretacao: 'Score mais alto = rede hospitalar sob mais pressão simultânea. Útil como "monitor" de sobrecarga para acompanhar ao longo do tempo (rode o mesmo índice em anos sucessivos e compare).',
    },
    {
        key: 'hei', titulo: 'Healthcare Equity Index', sigla: 'HEI', grupo: 'Equidade',
        descricao: 'Desigualdade de acesso aos recursos do SUS ENTRE os municípios de uma UF — Gini, Theil, Hoover e Palma sobre a distribuição de leitos/médicos/enfermeiros/eSF por habitante.',
        colunaScore: 'HEI',
        estatisticaEstadual: true,
        componentes: [
            { coluna: 'GINI_RECURSOS_SAUDE_HEI', label: 'Gini' },
            { coluna: 'THEIL_RECURSOS_SAUDE_HEI', label: 'Theil' },
            { coluna: 'HOOVER_RECURSOS_SAUDE_HEI', label: 'Hoover' },
            { coluna: 'PALMA_RECURSOS_SAUDE_HEI', label: 'Palma' },
        ],
        interpretacao: 'Diferente dos demais índices, o HEI é uma propriedade da UF inteira, não de um único município — por isso o mesmo valor aparece em todos os municípios daquela UF/ano. Score mais alto = recursos de saúde mais concentrados em poucos municípios (tipicamente a capital/polos regionais).',
    },
];

export const getIndiceSpec = (key) => INDICES_COMPOSTOS_SPEC.find((i) => i.key === key);
