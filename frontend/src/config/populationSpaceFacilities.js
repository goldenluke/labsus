// Estabelecimentos reais já explorados nesta sessão (top por volume de Hospitalization
// na BPHO) -- uf="SP" conferido manualmente para os 3 primeiros; os demais podem não
// ter composição demográfica se estiverem em outra UF (ausência estrutural, não erro).
export const KNOWN_FACILITIES = [
    { facility_uri: 'facility_2077396', label: 'facility_2077396 (SP)', uf: 'SP' },
    { facility_uri: 'facility_2082187', label: 'facility_2082187 (SP)', uf: 'SP' },
    { facility_uri: 'facility_0000434', label: 'facility_0000434 (SP)', uf: 'SP' },
    { facility_uri: 'facility_0013846', label: 'facility_0013846', uf: null },
    { facility_uri: 'facility_0009717', label: 'facility_0009717', uf: null },
    { facility_uri: 'facility_2522691', label: 'facility_2522691', uf: null },
    { facility_uri: 'facility_2237601', label: 'facility_2237601', uf: null },
    { facility_uri: 'facility_2748223', label: 'facility_2748223', uf: null },
    { facility_uri: 'facility_2270609', label: 'facility_2270609', uf: null },
    { facility_uri: 'facility_2781859', label: 'facility_2781859', uf: null },
    { facility_uri: 'facility_7743068', label: 'facility_7743068', uf: null },
    { facility_uri: 'facility_5718368', label: 'facility_5718368', uf: null },
    { facility_uri: 'facility_2688689', label: 'facility_2688689', uf: null },
    { facility_uri: 'facility_2705982', label: 'facility_2705982', uf: null },
];

// Top-15 estabelecimentos de ATENÇÃO PRIMÁRIA (ESF/SIA) por número de vínculos
// com equipe na BPHO -- população estruturalmente disjunta dos hospitais acima
// (ver PrimaryCareWorkforceDomain, ontologia-conceitual.md Fase 64).
export const KNOWN_PRIMARY_CARE_FACILITIES = [
    'facility_2096366', 'facility_0008702', 'facility_2040204', 'facility_2025914',
    'facility_2061171', 'facility_2039168', 'facility_2054256', 'facility_3806367',
    'facility_2824868', 'facility_2093650', 'facility_2065126', 'facility_6957323',
    'facility_2089831', 'facility_2044005', 'facility_2023288',
].map(uri => ({ facility_uri: uri, label: uri, uf: null }));

// Competências reais já confirmadas com dado carregado (usadas pelo módulo de
// transições, que precisa de mais de um mês por estabelecimento).
export const KNOWN_COMPETENCIAS = [
    { ano: 2025, mes: 10, label: '10/2025' },
    { ano: 2025, mes: 11, label: '11/2025' },
    { ano: 2025, mes: 12, label: '12/2025' },
];

export const DEFAULT_ANO = 2025;
export const DEFAULT_MES = 12;
