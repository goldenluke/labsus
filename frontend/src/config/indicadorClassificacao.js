// src/config/indicadorClassificacao.js

// Classificação dos indicadores da pipeline de Integração em dois eixos
// independentes: sistema de origem DATASUS (fonte primária dos dados) e
// domínio temático (agrupamento estilo RIPSA). Usada só para organizar a
// UI de seleção — não afeta o cálculo em si (isso continua em
// INDICADOR_TO_FEATURE_MODULE, no backend).

export const SISTEMAS_ORIGEM = {
    SIM: 'SIM — Sistema de Informações sobre Mortalidade',
    SINASC: 'SINASC — Sistema de Informações sobre Nascidos Vivos',
    SIH: 'SIH — Sistema de Informações Hospitalares',
    SIA: 'SIA — Sistema de Informações Ambulatoriais',
    SINAN: 'SINAN — Sistema de Informação de Agravos de Notificação',
    CNES: 'CNES — Cadastro Nacional de Estabelecimentos de Saúde',
    MULTISSISTEMA: 'Multissistema (combina 2+ fontes)',
};

export const ORDEM_SISTEMAS = ['SIM', 'SINASC', 'SIH', 'SIA', 'SINAN', 'CNES', 'MULTISSISTEMA'];

export const DOMINIOS = {
    MORTALIDADE: 'Mortalidade Geral e por Causas',
    MATERNO_INFANTIL: 'Saúde Materno-Infantil',
    TRANSMISSIVEIS: 'Doenças Transmissíveis e Agravos',
    CRONICAS_APS: 'Doenças Crônicas e Acesso à Atenção Primária',
    TRABALHADOR: 'Saúde do Trabalhador',
    VIOLENCIA: 'Violência e Causas Externas',
    RECURSOS: 'Assistência e Recursos de Saúde',
    HOSPITALAR: 'Utilização e Desempenho Hospitalar',
    QUALIDADE_INFO: 'Qualidade da Informação',
};

export const ORDEM_DOMINIOS = [
    'MORTALIDADE', 'MATERNO_INFANTIL', 'TRANSMISSIVEIS', 'CRONICAS_APS',
    'TRABALHADOR', 'VIOLENCIA', 'RECURSOS', 'HOSPITALAR', 'QUALIDADE_INFO',
];

// key do indicador -> { sistema, dominio }. Ambos são chaves de SISTEMAS_ORIGEM/DOMINIOS.
export const INDICADOR_CLASSIFICACAO = {
    // --- Saúde Materno-Infantil ---
    'TMI': { sistema: 'MULTISSISTEMA', dominio: 'MATERNO_INFANTIL' }, // óbitos (SIM) / nascidos vivos (SINASC)
    'COBERTURA_PRENATAL': { sistema: 'SINASC', dominio: 'MATERNO_INFANTIL' },
    'PROP_CESAREOS': { sistema: 'SINASC', dominio: 'MATERNO_INFANTIL' },
    'PROP_MAE_ADOL': { sistema: 'SINASC', dominio: 'MATERNO_INFANTIL' },
    'IND_ADEQUACAO_UTI_NEONATAL': { sistema: 'MULTISSISTEMA', dominio: 'MATERNO_INFANTIL' }, // nascidos baixo peso (SINASC) / leitos UTI neonatal (CNES)

    // --- Qualidade da Informação ---
    'PROP_MAL_DEFINIDAS': { sistema: 'SIM', dominio: 'QUALIDADE_INFO' },
    'IQI_QUALIDADE_INFORMACAO': { sistema: 'MULTISSISTEMA', dominio: 'QUALIDADE_INFO' }, // SIM+SINASC

    // --- Doenças Crônicas e Acesso à Atenção Primária ---
    'DOENCAS_CRONICAS': { sistema: 'SIH', dominio: 'CRONICAS_APS' },
    'ICSAP': { sistema: 'SIH', dominio: 'CRONICAS_APS' },
    'ICSAP_PROP': { sistema: 'SIH', dominio: 'CRONICAS_APS' },
    'TAXA_EQUIPES_ESF': { sistema: 'CNES', dominio: 'CRONICAS_APS' },
    'TAXA_RESOLUTIVIDADE_AMBULATORIAL': { sistema: 'MULTISSISTEMA', dominio: 'CRONICAS_APS' }, // procedimentos (SIA) / internações ICSAP (SIH)
    'TAXA_COBERTURA_CITOPATOLOGICO': { sistema: 'SIA', dominio: 'CRONICAS_APS' },
    'TAXA_COBERTURA_MAMOGRAFIA': { sistema: 'SIA', dominio: 'CRONICAS_APS' },

    // --- Utilização e Desempenho Hospitalar ---
    'IND_CARGA_HOSPITALAR_ESF': { sistema: 'MULTISSISTEMA', dominio: 'HOSPITALAR' }, // internações (SIH) / equipes ESF (CNES)
    'TAXA_INTERNACAO_GERAL': { sistema: 'SIH', dominio: 'HOSPITALAR' },
    'IND_COMPLEXIDADE_HOSPITALAR': { sistema: 'SIH', dominio: 'HOSPITALAR' },
    'SHANNON_DIVERSIDADE_INTERNACOES': { sistema: 'SIH', dominio: 'HOSPITALAR' },
    'IND_ESPECIALIZACAO_HOSPITALAR': { sistema: 'SIH', dominio: 'HOSPITALAR' },
    'IND_PRESSAO_LEITOS': { sistema: 'MULTISSISTEMA', dominio: 'HOSPITALAR' }, // internações (SIH) / leitos (CNES)
    'IND_RESOLUTIVIDADE': { sistema: 'SIH', dominio: 'HOSPITALAR' },
    'TMH_HOSPITALAR_PADRONIZADA': { sistema: 'SIH', dominio: 'HOSPITALAR' },

    // --- Assistência e Recursos de Saúde ---
    'TAXA_MEDICOS': { sistema: 'CNES', dominio: 'RECURSOS' },
    'IND_CAPACIDADE_ASSISTENCIAL': { sistema: 'CNES', dominio: 'RECURSOS' },
    'IND_COBERTURA_ASSISTENCIAL': { sistema: 'CNES', dominio: 'RECURSOS' },
    'SHANNON_DIVERSIDADE_ASSISTENCIAL': { sistema: 'CNES', dominio: 'RECURSOS' },

    // --- Doenças Transmissíveis e Agravos (SINAN) ---
    'TAXA_DETECCAO_HANSENIASE': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCID_DENGUE': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCID_CHIKUNGUNYA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCID_ZIKA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_TB': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_ABANDONO_TB': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_CURA_TB': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_CHAGAS': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_ESQU': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_MALARIA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_LEIV': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_LTAN': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_HEPATITES': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_SIFA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_SIFG': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_SIFC': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_CONF_ANIMAIS_P': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_RAIVA_HUMANA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_LEPTO': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_MENI': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_DIFT': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_COQU': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_FTIF': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_HANTAVIROSE': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_SARAMPO': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_RUBEOLA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_FMAC': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_BOTULISMO': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_COLERA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_PESTE': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_NOTIFICACAO_PARALISIA_FLACIDA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_SRC': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_TETANO_ACIDENTAL': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_TETANO_NEONATAL': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_TOXOPLASMOSE_CONGENITA': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },
    'TAXA_INCIDENCIA_TOXOPLASMOSE_GESTACIONAL': { sistema: 'SINAN', dominio: 'TRANSMISSIVEIS' },

    // --- Saúde do Trabalhador (SINAN) ---
    'TAXA_ACIDENTE_TRABALHO': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_DERM': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_CANCER_TRAB': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_ACBI': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_LERDORT': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_TRANSTORNO_MENTAL_TRAB': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_PAIR': { sistema: 'SINAN', dominio: 'TRABALHADOR' },
    'TAXA_NOTIFICACAO_PNEUMOCONIOSE': { sistema: 'SINAN', dominio: 'TRABALHADOR' },

    // --- Violência e Causas Externas ---
    'TAXA_INTOX_EXOGENA': { sistema: 'SINAN', dominio: 'VIOLENCIA' },
    'TAXA_NOTIFICACAO_VIOLENCIA': { sistema: 'SINAN', dominio: 'VIOLENCIA' },
    'TAXA_MORT_EXTERNAS': { sistema: 'SIM', dominio: 'VIOLENCIA' },

    // --- Mortalidade Geral e por Causas ---
    'TAXA_MORT_PREM_DCNT': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'TAXA_MORT_CIRCULATORIO': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'TAXA_MORT_NEOPLASIAS': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'TAXA_MORT_RESPIRATORIAS': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'TAXA_MORT_DIABETES': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'TAXA_MORT_COVID19': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'TAXA_MORTALIDADE_GERAL': { sistema: 'SIM', dominio: 'MORTALIDADE' },
    'SHANNON_DIVERSIDADE_OBITOS': { sistema: 'SIM', dominio: 'MORTALIDADE' },
};

// Fallback para qualquer indicador novo que ainda não tenha sido classificado
// (evita que ele desapareça da UI — cai numa seção "Não classificado").
export const CLASSIFICACAO_PADRAO = { sistema: 'MULTISSISTEMA', dominio: 'MORTALIDADE' };
