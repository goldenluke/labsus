// === Início do arquivo: src/config/fileTypes.js (NOVO ARQUIVO) ===

export const FILE_TYPE_LABELS = {
    'INDICATORS': 'Indicadores de Saúde',
    'K_MEANS': 'Perfis de Saúde',
    'PREDICTION': 'Previsão de Internações',
    'ARCHETYPE': 'Definição de Arquétipos',
    'OTHER': 'Outro',
    'ALL': 'Todos os Tipos' // Usado no filtro do CsvManager
};

// Mapeamento para o placeholder do seletor (um pouco mais específico)
export const FILE_TYPE_PLACEHOLDERS = {
    'INDICATORS': 'arquivos de Indicadores de Saúde',
    'K_MEANS': 'arquivos de Perfis de Saúde',
    'PREDICTION': 'arquivos de Previsão',
    'ARCHETYPE': 'arquivos de Arquétipos',
    'OTHER': 'outros tipos de arquivos',
};

// ... você pode adicionar ícones e cores aqui também no futuro para centralizar tudo
