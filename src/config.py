# src/config.py

# Dicionário central que mapeia os nomes técnicos dos indicadores para rótulos amigáveis.
INDICADORES_MAP = {
    # Indicadores Originais
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
    'PROP_MAE_ADOL': 'Proporção de Nascidos Vivos de Mães com Menos de 20 Anos (%)',
    'TAXA_DETECCAO_HANSENIASE': 'Taxa de Detecção de Hanseníase (por 100 mil hab.)',
    'TAXA_INTERNACAO_GERAL': 'Taxa de Internação Hospitalar (por 10 mil hab.)',
    'TAXA_EQUIPES_ESF': 'Taxa de Cobertura da Estratégia Saúde da Família (%)',

    # Novos Indicadores
    'TAXA_INCID_DENGUE': 'Taxa de Incidência de Dengue (por 100.000 hab.)',
    'TAXA_INCID_CHIKUNGUNYA': 'Taxa de Incidência de Chikungunya (por 100.000 hab.)',
    'TAXA_INCID_ZIKA': 'Taxa de Incidência de Zika (por 100.000 hab.)',
    'TAXA_INCIDENCIA_TB': 'Taxa de Incidência de Tuberculose (por 100.000 hab.)',
    'TAXA_ABANDONO_TB': 'Taxa de Abandono de Tratamento de TB (%)',
    'TAXA_CURA_TB': 'Taxa de Cura de Tuberculose (%)',
    'TAXA_MORT_PREM_DCNT': 'Mortalidade Prematura por DCNT (por 100.000 hab.)',
    'TAXA_MORT_CIRCULATORIO': 'Mortalidade por Doenças Circulatórias (por 100.000 hab.)',
    'TAXA_MORT_NEOPLASIAS': 'Mortalidade por Neoplasias (por 100.000 hab.)',
    'TAXA_MORT_RESPIRATORIAS': 'Mortalidade por Doenças Respiratórias (por 100.000 hab.)',
    'TAXA_MORT_DIABETES': 'Mortalidade por Diabetes (por 100.000 hab.)',
    'TAXA_MORT_EXTERNAS': 'Mortalidade por Causas Externas (por 100.000 hab.)',
    'TAXA_MORT_COVID19': 'Mortalidade por COVID-19 (por 100.000 hab.)',
}

# Lista de chaves dos indicadores, gerada dinamicamente para consistência.
LISTA_INDICADORES = list(INDICADORES_MAP.keys())

# Dicionário que define se um indicador é "melhor" quando seu valor é alto ou baixo.
INDICADOR_POLARIDADE = {
    # Melhor quando MAIOR
    'COBERTURA_PRENATAL': 'high', 'TAXA_MEDICOS': 'high', 'TAXA_EQUIPES_ESF': 'high', 'TAXA_CURA_TB': 'high',
    'TAXA_RESOLUTIVIDADE_AMBULATORIAL': 'high',

    # Melhor quando MENOR
    'TMI': 'low', 'PROP_CESAREOS': 'low', 'PROP_MAL_DEFINIDAS': 'low', 'DOENCAS_CRONICAS': 'low',
    'ICSAP': 'low', 'ICSAP_PROP': 'low',
    'IND_CARGA_HOSPITALAR_ESF': 'low', 'IND_ADEQUACAO_UTI_NEONATAL': 'low',
    'PROP_MAE_ADOL': 'low', 'TAXA_DETECCAO_HANSENIASE': 'low', 'TAXA_INTERNACAO_GERAL': 'low',
    'TAXA_INCID_DENGUE': 'low', 'TAXA_INCID_CHIKUNGUNYA': 'low', 'TAXA_INCID_ZIKA': 'low',
    'TAXA_INCIDENCIA_TB': 'low', 'TAXA_ABANDONO_TB': 'low', 'TAXA_MORT_PREM_DCNT': 'low',
    'TAXA_MORT_CIRCULATORIO': 'low', 'TAXA_MORT_NEOPLASIAS': 'low', 'TAXA_MORT_RESPIRATORIAS': 'low',
    'TAXA_MORT_DIABETES': 'low', 'TAXA_MORT_EXTERNAS': 'low', 'TAXA_MORT_COVID19': 'low',
}
