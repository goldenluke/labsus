// src/components/common/FilterControls.jsx

import React from 'react';
import { useMemo } from 'react'; // Para useMemo interno
// Os mapeamentos de config (UF_CONFIGS, INDICADORES_MAP) não são necessários aqui se as opções já vêm pré-formatadas.
// import { UF_CONFIGS } from '../../config/ufConfigs';
// import { INDICADORES_MAP } from '../../config/indicadores';

const FilterControls = ({
    // Props relacionadas ao arquivo de dados (para IndicadoresViewerPage)
    availableFiles, selectedFileId, setSelectedFileId,

    // Filtros principais (UF, Ano, Indicador)
    selectedUf, setSelectedUf, availableUfs, // availableUfs já vem formatada do hook
    selectedYear, setSelectedYear, availableYears,
    selectedIndicator, setSelectedIndicator, availableIndicators,

    // Filtros para gráficos de dispersão
    scatterX, setScatterX, scatterY, setScatterY,

    // Props específicas do K-Means (passadas para FilterControls, mas não usadas aqui diretamente)
    selectedClusterId, setSelectedClusterId, availableClusters,
    selectedProfile, setSelectedProfile, availableProfiles,
    activeTab, // Para adaptar a visibilidade de controles dentro deste componente (se precisar)
ufCompLeft, setUfCompLeft, yearCompLeft, setYearCompLeft,
ufCompRight, setUfCompRight, yearCompRight, setYearCompRight,
ufTransicao, setUfTransicao, yearTransicaoInitial, setYearTransicaoInitial, yearTransicaoFinal, setYearTransicaoFinal,
animationYear, availableYears: availableAnimationYears, // Renomeado para evitar conflito com availableYears geral
}) => {

    return (
        <>
        {/* Controle de Seleção de Arquivo (apenas se as props relevantes estiverem presentes) */}
        {availableFiles && setSelectedFileId && (
            <label className="flex flex-col">
            Arquivo de Dados:
            <select
            value={selectedFileId}
            onChange={(e) => setSelectedFileId(e.target.value)}
            className="p-2 border rounded-md"
            >
            <option value="">Selecione um arquivo</option>
            {Array.isArray(availableFiles) && availableFiles.map(file => (
                <option key={file.id} value={file.id}>
                {file.filename} (Upload: {new Date(file.uploaded_at).toLocaleDateString()})
                </option>
            ))}
            </select>
            </label>
        )}

        {/* Controle de UF - Visível em todos os dashboards que usam UF (Indicadores, K-Means) */}
        {availableUfs && setSelectedUf && ( // Garante que as props para UF estejam presentes
            <label className="flex flex-col">
            Estado (UF):
            <select
            value={selectedUf}
            onChange={(e) => setSelectedUf(e.target.value)}
            className="p-2 border rounded-md"
            >
            <option value="BR">Brasil</option> {/* Opção para o Brasil inteiro */}
            {Array.isArray(availableUfs) && availableUfs.map(ufCode => (
                <option key={ufCode} value={ufCode}>{ufCode}</option>
            ))}
            </select>
            </label>
        )}

        {/* Controle de Ano - Visível em todos os dashboards que usam Ano */}
        {availableYears && setSelectedYear && ( // Garante que as props para Ano estejam presentes
            // Somente mostra se a aba ativa não for 'animacao' ou 'mapa-transicao'
            // (essas abas têm seus próprios controles de ano)
            // Ou se activeTab não for passado (para dashboards que não usam abas complexas)
            (activeTab !== 'animacao' && activeTab !== 'mapa-transicao') && (
                <label className="flex flex-col">
                Ano:
                <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                className="p-2 border rounded-md"
                >
                {Array.isArray(availableYears) && availableYears.map(year => (
                    <option key={year} value={year}>{year}</option>
                ))}
                </select>
                </label>
            )
        )}

        {/* Controle de Indicador Principal - Relevante para IndicadoresViewer e K-Means (Radar) */}
        {availableIndicators && setSelectedIndicator && ( // Garante que as props estejam presentes
            (activeTab === 'visao-geral' || activeTab === 'analise-estado' || !activeTab) && ( // Mostra se é aba de indicadores ou sem aba definida
            <label className="flex flex-col">
            Indicador Principal:
            <select
            value={selectedIndicator}
            onChange={(e) => setSelectedIndicator(e.target.value)}
            className="p-2 border rounded-md"
            >
            {Array.isArray(availableIndicators) && availableIndicators.map(indicatorKey => (
                <option key={indicatorKey} value={indicatorKey}>
                {/* INDICADORES_MAP é importado nos componentes de TabContent, não aqui */}
                {indicatorKey} {/* Exibe a chave, o TabContent fará o mapeamento do label */}
                </option>
            ))}
            </select>
            </label>
            )
        )}

        {/* Controles de Scatter (Eixo X e Y) - Relevante para Visão Geral e Análise por Estado/Município */}
        {availableIndicators && setScatterX && setScatterY && ( // Garante que as props estejam presentes
            (activeTab === 'visao-geral' || activeTab === 'analise-estado' || activeTab === 'analise-municipio' || !activeTab) && ( // Mostra se é aba de indicadores ou sem aba
            <>
            <label className="flex flex-col">
            Eixo X (Correlação):
            <select
            value={scatterX}
            onChange={(e) => setScatterX(e.target.value)}
            className="p-2 border rounded-md"
            >
            {Array.isArray(availableIndicators) && availableIndicators.map(indicatorKey => (
                <option key={indicatorKey} value={indicatorKey}>
                {indicatorKey}
                </option>
            ))}
            </select>
            </label>
            <label className="flex flex-col">
            Eixo Y (Correlação):
            <select
            value={scatterY}
            onChange={(e) => setScatterY(e.target.value)}
            className="p-2 border rounded-md"
            >
            {Array.isArray(availableIndicators) && availableIndicators.map(indicatorKey => (
                <option key={indicatorKey} value={indicatorKey}>
                {indicatorKey}
                </option>
            ))}
            </select>
            </label>
            </>
            )
        )}

        {/* Filtros específicos de K-Means (clusters e perfis) */}
        {availableClusters && setSelectedClusterId && ( // Garante que as props de cluster estejam presentes
            activeTab === 'mapa-principal' && ( // Apenas na aba principal do K-Means
            <>
            <label className="flex flex-col">
            Número do Cluster:
            <select
            value={selectedClusterId}
            onChange={(e) => setSelectedClusterId(e.target.value === '' ? null : parseInt(e.target.value))}
            className="p-2 border rounded-md"
            disabled={availableClusters.length === 0}
            >
            <option value="">Todos os Clusters</option>
            {Array.isArray(availableClusters) && availableClusters.map(clusterNum => (
                <option key={clusterNum} value={clusterNum}>{clusterNum}</option>
            ))}
            </select>
            </label>

            <label className="flex flex-col">
            Perfil de Saúde:
            <select
            value={selectedProfile}
            onChange={(e) => setSelectedProfile(e.target.value)}
            className="p-2 border rounded-md"
            disabled={availableProfiles.length === 0}
            >
            <option value="">Todos os Perfis</option>
            {Array.isArray(availableProfiles) && availableProfiles.map(profileName => (
                <option key={profileName} value={profileName}>{profileName}</option>
            ))}
            </select>
            </label>
            </>
            )
        )}

        {/* Filtros específicos de comparação de mapas (K-Means) */}
        {availableYears && availableUfs && setUfCompLeft && setYearCompLeft && setUfCompRight && setYearCompRight && (
            activeTab === 'mapa-comparacao' && (
                <>
                <label className="flex flex-col">
                Ano Esquerdo:
                <select
                value={yearCompLeft}
                onChange={(e) => setYearCompLeft(parseInt(e.target.value))}
                className="p-2 border rounded-md"
                >
                {Array.isArray(availableYears) && availableYears.map(year => (<option key={`comp-left-${year}`} value={year}>{year}</option>))}
                </select>
                </label>
                <label className="flex flex-col">
                Ano Direito:
                <select
                value={yearCompRight}
                onChange={(e) => setYearCompRight(parseInt(e.target.value))}
                className="p-2 border rounded-md"
                >
                {Array.isArray(availableYears) && availableYears.map(year => (<option key={`comp-right-${year}`} value={year}>{year}</option>))}
                </select>
                </label>
                <label className="flex flex-col">
                UF Esquerda:
                <select
                value={ufCompLeft}
                onChange={(e) => setUfCompLeft(e.target.value)}
                className="p-2 border rounded-md"
                >
                <option value="BR">Brasil</option>
                {Array.isArray(availableUfs) && availableUfs.map(ufCode => (<option key={`uf-left-${ufCode}`} value={ufCode}>{ufCode}</option>))}
                </select>
                </label>
                <label className="flex flex-col">
                UF Direita:
                <select
                value={ufCompRight}
                onChange={(e) => setUfCompRight(e.target.value)}
                className="p-2 border rounded-md"
                >
                <option value="BR">Brasil</option>
                {Array.isArray(availableUfs) && availableUfs.map(ufCode => (<option key={`uf-right-${ufCode}`} value={ufCode}>{ufCode}</option>))}
                </select>
                </label>
                </>
            )
        )}

        {/* Filtros para animação (K-Means) - apenas um ano, mas precisa do controle externo de reprodução */}
        {availableYears && (
            activeTab === 'animacao' && (
                <label className="flex flex-col">
                Ano da Animação:
                <select
                value={animationYear}
                onChange={(e) => availableAnimationYears.length > 0 && animationYear && animationYear !== parseInt(e.target.value) && (console.log('Animation year changed to:', e.target.value), false) && parseInt(e.target.value)} // Evita re-render se não for diferente
                className="p-2 border rounded-md"
                disabled={true} // Desabilitado pois o ano muda pela animação
                >
                {/* Apenas o ano atual da animação */}
                {animationYear && <option value={animationYear}>{animationYear}</option>}
                </select>
                <p className="text-xs text-gray-500 mt-1">O ano muda automaticamente na animação.</p>
                </label>
            )
        )}
        </>
    );
};

export default FilterControls;
