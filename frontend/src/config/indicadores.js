// src/config/indicadores.js

// Dicionário central que mapeia os nomes técnicos dos indicadores para rótulos amigáveis.
// Ao usar 'export', tornamos esta variável disponível para ser importada em outros arquivos.
export const INDICADORES_MAP = {
    // Indicadores Originais
    'TMI': 'Taxa de Mortalidade Infantil (por 1.000 nascidos vivos)',
    'COBERTURA_PRENATAL': 'Cobertura de Pré-Natal Adequado (7+ consultas) (%)',
    'TAXA_MEDICOS': 'Médicos por 1.000 habitantes',
    'PROP_CESAREOS': 'Proporção de Partos Cesáreos (%)',
    'PROP_MAL_DEFINIDAS': 'Proporção de Óbitos por Causas Mal Definidas (%)',
    'DOENCAS_CRONICAS': 'Internações por Doenças Crônicas Selecionadas (Hipertensão/Diabetes/Asma, por 10 mil hab.)',
    'ICSAP': 'Taxa de Internações por Condições Sensíveis à Atenção Primária (ICSAP, por 10 mil hab.)',
    'ICSAP_PROP': 'Proporção de Internações por Condições Sensíveis à Atenção Primária (%)',
    'IND_CARGA_HOSPITALAR_ESF': 'Índice de Carga Hospitalar por Equipe ESF (SIH+CNES: internações/equipe)',
    'IND_ADEQUACAO_UTI_NEONATAL': 'Índice de Adequação de UTI Neonatal (SINASC+CNES: nascidos de baixo peso/leito)',
    'TAXA_RESOLUTIVIDADE_AMBULATORIAL': 'Taxa de Resolutividade Ambulatorial (SIA+SIH: procedimentos/internação ICSAP)',
    'TAXA_COBERTURA_CITOPATOLOGICO': 'Cobertura de Exame Citopatológico do Colo do Útero (SIA, rastreamento, por 1.000 hab.)',
    'TAXA_COBERTURA_MAMOGRAFIA': 'Cobertura de Mamografia de Rastreamento (SIA, por 1.000 hab.)',
    'PROP_MAE_ADOL': 'Proporção de Nascidos Vivos de Mães com Menos de 20 Anos (%)',
    'TAXA_DETECCAO_HANSENIASE': 'Taxa de Detecção de Hanseníase (por 100 mil hab.)',
    'TAXA_INTERNACAO_GERAL': 'Taxa de Internação Hospitalar (por 10 mil hab.)',
    'TAXA_EQUIPES_ESF': 'Cobertura da Estratégia Saúde da Família (%)',

    // Novos Indicadores de Arboviroses
    'TAXA_INCID_DENGUE': 'Taxa de Incidência de Dengue (por 100.000 hab.)',
    'TAXA_INCID_CHIKUNGUNYA': 'Taxa de Incidência de Chikungunya (por 100.000 hab.)',
    'TAXA_INCID_ZIKA': 'Taxa de Incidência de Zika (por 100.000 hab.)',

    // Novos Indicadores de Tuberculose
    'TAXA_INCIDENCIA_TB': 'Taxa de Incidência de Tuberculose (por 100.000 hab.)',
    'TAXA_ABANDONO_TB': 'Taxa de Abandono de Tratamento de TB (%)',
    'TAXA_CURA_TB': 'Taxa de Cura de Tuberculose (%)',

    // Novos Indicadores de Mortalidade
    'TAXA_MORT_PREM_DCNT': 'Mortalidade Prematura por DCNT (por 100.000 hab.)',
    'TAXA_MORT_CIRCULATORIO': 'Mortalidade por Doenças Circulatórias (por 100.000 hab.)',
    'TAXA_MORT_NEOPLASIAS': 'Mortalidade por Neoplasias (por 100.000 hab.)',
    'TAXA_MORT_RESPIRATORIAS': 'Mortalidade por Doenças Respiratórias (por 100.000 hab.)',
    'TAXA_MORT_DIABETES': 'Mortalidade por Diabetes (por 100.000 hab.)',
    'TAXA_MORT_EXTERNAS': 'Mortalidade por Causas Externas (por 100.000 hab.)',
    'TAXA_MORT_COVID19': 'Mortalidade por COVID-19 (por 100.000 hab.)',

    // Novos Indicadores de Agravos do SINAN
    'TAXA_INCIDENCIA_CHAGAS': 'Taxa de Incidência de Doença de Chagas Aguda (por 100.000 hab.)',
    'TAXA_INCIDENCIA_ESQU': 'Taxa de Incidência de Esquistossomose (por 100.000 hab.)',
    'TAXA_INCIDENCIA_MALARIA': 'Taxa de Incidência de Malária (por 100.000 hab.)',
    'TAXA_INCIDENCIA_LEIV': 'Taxa de Incidência de Leishmaniose Visceral (por 100.000 hab.)',
    'TAXA_INCIDENCIA_LTAN': 'Taxa de Incidência de Leishmaniose Tegumentar (por 100.000 hab.)',
    'TAXA_INCIDENCIA_HEPATITES': 'Taxa de Incidência de Hepatites Virais (por 100.000 hab.)',
    'TAXA_INCIDENCIA_SIFA': 'Taxa de Incidência de Sífilis Adquirida (por 100.000 hab.)',
    'TAXA_INCIDENCIA_SIFG': 'Taxa de Incidência de Sífilis em Gestante (por 100.000 hab.)',
    'TAXA_INCIDENCIA_SIFC': 'Taxa de Incidência de Sífilis Congênita (por 100.000 hab.)',
    'TAXA_CONF_ANIMAIS_P': 'Taxa de Acidentes por Animais Peçonhentos (por 100.000 hab.)',
    'TAXA_RAIVA_HUMANA': 'Taxa de Raiva Humana (por 100.000 hab.)',
    'TAXA_INCIDENCIA_LEPTO': 'Taxa de Incidência de Leptospirose (por 100.000 hab.)',
    'TAXA_INCIDENCIA_MENI': 'Taxa de Incidência de Meningite (por 100.000 hab.)',
    'TAXA_INCIDENCIA_DIFT': 'Taxa de Incidência de Difteria (por 100.000 hab.)',
    'TAXA_INCIDENCIA_COQU': 'Taxa de Incidência de Coqueluche (por 100.000 hab.)',
    'TAXA_ACIDENTE_TRABALHO': 'Taxa de Acidente de Trabalho Grave (por 100.000 hab.)',
    'TAXA_INTOX_EXOGENA': 'Taxa de Intoxicação Exógena (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_VIOLENCIA': 'Taxa de Notificação de Violência Interpessoal/Autoprovocada (por 100.000 hab.)',
    'TAXA_INCIDENCIA_FTIF': 'Taxa de Incidência de Febre Tifóide (por 100.000 hab.)',
    'TAXA_INCIDENCIA_HANTAVIROSE': 'Taxa de Incidência de Hantavirose (por 100.000 hab.)',
    'TAXA_INCIDENCIA_SARAMPO': 'Taxa de Incidência de Sarampo (por 100.000 hab.)',
    'TAXA_INCIDENCIA_RUBEOLA': 'Taxa de Incidência de Rubéola (por 100.000 hab.)',
    'TAXA_INCIDENCIA_FMAC': 'Taxa de Incidência de Febre Maculosa (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_DERM': 'Taxa de Notificação de Dermatoses Ocupacionais (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_CANCER_TRAB': 'Taxa de Notificação de Câncer Relacionado ao Trabalho (por 100.000 hab.)',
    'TAXA_INCIDENCIA_BOTULISMO': 'Taxa de Incidência de Botulismo (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_ACBI': 'Taxa de Notificação de Acidente c/ Material Biológico (por 100.000 hab.)',

    // Mais Indicadores de Agravos do SINAN
    'TAXA_INCIDENCIA_COLERA': 'Taxa de Incidência de Cólera (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_LERDORT': 'Taxa de Notificação de LER/DORT Relacionado ao Trabalho (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_TRANSTORNO_MENTAL_TRAB': 'Taxa de Notificação de Transtorno Mental Relacionado ao Trabalho (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_PAIR': 'Taxa de Notificação de Perda Auditiva Induzida por Ruído (Trabalho) (por 100.000 hab.)',
    'TAXA_INCIDENCIA_PESTE': 'Taxa de Incidência de Peste (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_PARALISIA_FLACIDA': 'Taxa de Notificação de Paralisia Flácida Aguda (por 100.000 hab.)',
    'TAXA_NOTIFICACAO_PNEUMOCONIOSE': 'Taxa de Notificação de Pneumoconiose Relacionada ao Trabalho (por 100.000 hab.)',
    'TAXA_INCIDENCIA_SRC': 'Taxa de Incidência de Síndrome da Rubéola Congênita (por 100.000 hab.)',
    'TAXA_INCIDENCIA_TETANO_ACIDENTAL': 'Taxa de Incidência de Tétano Acidental (por 100.000 hab.)',
    'TAXA_INCIDENCIA_TETANO_NEONATAL': 'Taxa de Incidência de Tétano Neonatal (por 100.000 hab.)',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_CONGENITA': 'Taxa de Incidência de Toxoplasmose Congênita (por 100.000 hab.)',
    'TAXA_INCIDENCIA_TOXOPLASMOSE_GESTACIONAL': 'Taxa de Incidência de Toxoplasmose Gestacional (por 100.000 hab.)',

    // Índices Compostos (agregações diretas, sem linkage nem modelo)
    'IND_CAPACIDADE_ASSISTENCIAL': 'Índice de Capacidade Assistencial (CNES: leitos/médicos/enfermeiros/eSF)',
    'IND_COMPLEXIDADE_HOSPITALAR': 'Índice de Complexidade Hospitalar (SIH: procedimentos/CIDs distintos)',
    'SHANNON_DIVERSIDADE_OBITOS': 'Diversidade Epidemiológica — Óbitos (Shannon, SIM)',
    'SHANNON_DIVERSIDADE_INTERNACOES': 'Diversidade Epidemiológica — Internações (Shannon, SIH)',
    'IND_ESPECIALIZACAO_HOSPITALAR': 'Índice de Especialização Hospitalar (% no capítulo CID principal)',
    'IND_PRESSAO_LEITOS': 'Índice de Pressão Hospitalar (internações por leito)',
    'IND_RESOLUTIVIDADE': 'Índice de Resolutividade Hospitalar (% alta sem óbito)',
    'IND_COBERTURA_ASSISTENCIAL': 'Índice de Cobertura Assistencial (CNES: UBS/hospitais/eSF por habitante)',
    'SHANNON_DIVERSIDADE_ASSISTENCIAL': 'Índice de Diversidade Assistencial (Shannon dos tipos de estabelecimento)',
    'TMH_HOSPITALAR_PADRONIZADA': 'Mortalidade Hospitalar Ajustada por Idade (SIH, padronização direta)',
    'IQI_QUALIDADE_INFORMACAO': 'Índice de Qualidade da Informação (SIM+SINASC: completude de idade/sexo/raça/escolaridade)',
    'TAXA_MORTALIDADE_GERAL': 'Taxa de Mortalidade Geral (por 1.000 hab., SIM)',
};

