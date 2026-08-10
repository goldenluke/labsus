// src/config/polaridadeIndicadores.js

// Define se um valor MAIOR para o indicador é 'bom' ('high') ou 'ruim' ('low').
// Se 'low', significa que um valor MENOR é considerado 'bom'.

export const INDICADOR_POLARIDADE = {
    // Indicadores Originais
    'TMI': 'low', // Taxa de Mortalidade Infantil: menor é melhor
    'COBERTURA_PRENATAL': 'high', // Cobertura de Pré-Natal: maior é melhor
    'TAXA_MEDICOS': 'high', // Médicos por 1.000 habitantes: maior é melhor
    'PROP_CESAREOS': 'low', // Proporção de Partos Cesáreos: menor é melhor (idealmente, um range)
    'PROP_MAL_DEFINIDAS': 'low', // Proporção de Óbitos por Causas Mal Definidas: menor é melhor
    'DOENCAS_CRONICAS': 'low', // Internações por Doenças Crônicas Selecionadas: menor é melhor
    'ICSAP': 'low', // Taxa de Internações por Condições Sensíveis à Atenção Primária: menor é melhor (mais APS efetiva evita internação)
    'ICSAP_PROP': 'low', // Proporção de Internações por CSAP: menor é melhor
    'IND_CARGA_HOSPITALAR_ESF': 'low', // Internações por equipe ESF: menor é melhor (menos carga sobre a rede de APS)
    'IND_ADEQUACAO_UTI_NEONATAL': 'low', // Nascidos de baixo peso por leito de UTI neonatal: menor é melhor (mais capacidade frente à demanda)
    'TAXA_RESOLUTIVIDADE_AMBULATORIAL': 'high', // Procedimentos ambulatoriais por internação evitável: maior é melhor (rede ambulatorial resolvendo mais antes de virar internação)
    'PROP_MAE_ADOL': 'low', // Proporção de Nascidos Vivos de Mães com Menos de 20 Anos: menor é melhor
    'TAXA_DETECCAO_HANSENIASE': 'high', // Taxa de Detecção de Hanseníase: maior é melhor (significa que está detectando mais)
    'TAXA_INTERNACAO_GERAL': 'low', // Taxa de Internação Hospitalar: menor é melhor (pode indicar boa APS)
    'TAXA_EQUIPES_ESF': 'high', // Cobertura da Estratégia Saúde da Família: maior é melhor

    // Novos Indicadores de Arboviroses
    'TAXA_INCID_DENGUE': 'low', // Menor incidência é melhor
    'TAXA_INCID_CHIKUNGUNYA': 'low',
    'TAXA_INCID_ZIKA': 'low',

    // Novos Indicadores de Tuberculose
    'TAXA_INCIDENCIA_TB': 'low', // Menor incidência é melhor
    'TAXA_ABANDONO_TB': 'low', // Menor abandono é melhor
    'TAXA_CURA_TB': 'high', // Maior taxa de cura é melhor

    // Novos Indicadores de Mortalidade
    'TAXA_MORT_PREM_DCNT': 'low',
    'TAXA_MORT_CIRCULATORIO': 'low',
    'TAXA_MORT_NEOPLASIAS': 'low',
    'TAXA_MORT_RESPIRATORIAS': 'low',
    'TAXA_MORT_DIABETES': 'low',
    'TAXA_MORT_EXTERNAS': 'low',
    'TAXA_MORT_COVID19': 'low',

    // Novos Indicadores de Agravos do SINAN: em todos, menor incidência/notificação é melhor
    'TAXA_INCIDENCIA_CHAGAS': 'low',
    'TAXA_INCIDENCIA_ESQU': 'low',
    'TAXA_INCIDENCIA_MALARIA': 'low',
    'TAXA_INCIDENCIA_LEIV': 'low',
    'TAXA_INCIDENCIA_LTAN': 'low',
    'TAXA_INCIDENCIA_HEPATITES': 'low',
    'TAXA_INCIDENCIA_SIFA': 'low',
    'TAXA_INCIDENCIA_SIFG': 'low',
    'TAXA_INCIDENCIA_SIFC': 'low',
    'TAXA_CONF_ANIMAIS_P': 'low',
    'TAXA_RAIVA_HUMANA': 'low',
    'TAXA_INCIDENCIA_LEPTO': 'low',
    'TAXA_INCIDENCIA_MENI': 'low',
    'TAXA_INCIDENCIA_DIFT': 'low',
    'TAXA_INCIDENCIA_COQU': 'low',
    'TAXA_ACIDENTE_TRABALHO': 'low',
    'TAXA_INTOX_EXOGENA': 'low',
    'TAXA_NOTIFICACAO_VIOLENCIA': 'low',
    'TAXA_INCIDENCIA_FTIF': 'low',
    'TAXA_INCIDENCIA_HANTAVIROSE': 'low',
    'TAXA_INCIDENCIA_SARAMPO': 'low',
    'TAXA_INCIDENCIA_RUBEOLA': 'low',
    'TAXA_INCIDENCIA_FMAC': 'low',
    'TAXA_NOTIFICACAO_DERM': 'low',
    'TAXA_NOTIFICACAO_CANCER_TRAB': 'low',
    'TAXA_INCIDENCIA_BOTULISMO': 'low',
    'TAXA_NOTIFICACAO_ACBI': 'low',

    // Mais Indicadores de Agravos do SINAN: em todos, menor incidência/notificação é melhor
    'TAXA_INCIDENCIA_COLERA': 'low',
    'TAXA_NOTIFICACAO_LERDORT': 'low',
    'TAXA_NOTIFICACAO_TRANSTORNO_MENTAL_TRAB': 'low',
    'TAXA_NOTIFICACAO_PAIR': 'low',
    'TAXA_INCIDENCIA_PESTE': 'low',
    'TAXA_NOTIFICACAO_PARALISIA_FLACIDA': 'low',
    'TAXA_NOTIFICACAO_PNEUMOCONIOSE': 'low',
    'TAXA_INCIDENCIA_SRC': 'low',
    'TAXA_INCIDENCIA_TETANO_ACIDENTAL': 'low',
    'TAXA_INCIDENCIA_TETANO_NEONATAL': 'low',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_CONGENITA': 'low',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_GESTACIONAL': 'low',
    // ... e outros indicadores que você tiver
};
