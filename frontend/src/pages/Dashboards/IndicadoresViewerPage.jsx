// src/pages/Dashboards/IndicadoresViewerPage.jsx

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router-dom';

import useAnalysisData from '../../hooks/useAnalysisData';

import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FilterControls from '../../components/common/FilterControls';
import TabButtonsIndicadores from '../../components/common/TabButtonsIndicadores';

import VisaoGeralTabContent from '../../components/dashboards/indicadores/VisaoGeralTabContent';
import AnalisePorEstadoTabContent from '../../components/dashboards/indicadores/AnalisePorEstadoTabContent';
import AnalisePorMunicipioTabContent from '../../components/dashboards/indicadores/AnalisePorMunicipioTabContent';

import { FiDownload } from 'react-icons/fi';
import ExportPdfButton from '../../components/common/ExportPdfButton';


const IndicadoresViewerPage = () => {
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const fileIdFromUrl = queryParams.get('fileId');

    const [activeTab, setActiveTab] = useState('visao-geral');

    const contentToPrintRef = useRef(null);


    const {
        allData, loading, error,
        availableFiles, selectedFileId, setSelectedFileId,
        selectedFileDetails,
        selectedUf, setSelectedUf,
        selectedYear, setSelectedYear,
        selectedIndicator, setSelectedIndicator,
        scatterX, setScatterX, scatterY, setScatterY, // ⭐ DESESTRUTURANDO SETTERS AQUI ⭐
        rankingType, setRankingType,
        selectedMunicipality, setSelectedMunicipality,

        availableUfs, availableYears, availableIndicators,

        ufDataFilteredByYear, ufDataAllYears,
        ufMapConfig, geojson, loadingMap,
        mapChartData, mapTitle, municipalitiesForHistoricalComparison,
    } = useAnalysisData('BR', 2022, 'TMI', null, fileIdFromUrl);


    let feedbackMessage = null;

    if (error) {
        feedbackMessage = <FeedbackMessage message={`Erro: ${error}`} type="error" />;
    } else if (loading && availableFiles.length === 0 && !selectedFileId) {
        feedbackMessage = <FeedbackMessage message="A carregar lista de ficheiros do usuário..." />;
    } else if (!loading && availableFiles.length === 0 && !selectedFileId) {
        feedbackMessage = <FeedbackMessage message="Nenhum ficheiro CSV foi enviado para o seu usuário. Por favor, faça upload de um arquivo na página de gestão de ficheiros." type="info" />;
    } else if (!selectedFileId) {
        feedbackMessage = <FeedbackMessage message="Por favor, selecione um ficheiro de dados para começar." type="info" />;
    } else if (loading && selectedFileId) {
        feedbackMessage = <FeedbackMessage message="A carregar dados do ficheiro selecionado..." />;
    } else if (allData.length === 0 && !loading) {
        feedbackMessage = <FeedbackMessage message="O ficheiro selecionado está vazio ou não contém dados válidos. Por favor, verifique o conteúdo do arquivo CSV." type="error" />;
    } else if (availableIndicators.length === 0 && allData.length > 0) {
        feedbackMessage = <FeedbackMessage message="Nenhum indicador numérico foi identificado no ficheiro selecionado. Verifique as colunas e o formato numérico no CSV." type="error" />;
    } else if (!selectedIndicator && availableIndicators.length > 0) {
        feedbackMessage = <FeedbackMessage message="Por favor, selecione um indicador." type="info" />;
    } else if (availableYears.length === 0 && allData.length > 0) {
        feedbackMessage = <FeedbackMessage message="Nenhum ano identificado no ficheiro selecionado. Verifique a coluna 'ANO' no CSV." type="error" />;
    } else if (!selectedYear) {
        feedbackMessage = <FeedbackMessage message="Por favor, selecione um ano." type="info" />;
    }

    const filterControlsProps = {
        availableFiles, selectedFileId, setSelectedFileId,
        selectedUf, setSelectedUf, availableUfs,
        selectedYear, setSelectedYear, availableYears,
        selectedIndicator, setSelectedIndicator, availableIndicators,
        scatterX, setScatterX, scatterY, setScatterY, // ⭐ PASSANDO SETTERS AQUI ⭐

        selectedClusterId: null, setSelectedClusterId: () => {}, availableClusters: [],
        selectedProfile: null, setSelectedProfile: () => {}, availableProfiles: [],
        activeTab: null,
        ufCompLeft: null, setUfCompLeft: () => {}, yearCompLeft: null, setYearCompLeft: () => {},
        ufCompRight: null, setUfCompRight: () => {}, yearCompRight: null, setYearCompRight: () => {},
        ufTransicao: null, setUfTransicao: () => {}, yearTransicaoInitial: null, setYearTransicaoInitial: () => {}, yearTransicaoFinal: null, setYearTransicaoFinal: () => {},
        animationYear: null,
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
        Dashboards de Indicadores
        </h1>

        {/* Controles de Filtro Globais */}
        <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-wrap gap-4 items-center justify-center">
        <FilterControls {...filterControlsProps} />
        </div>

        {feedbackMessage && (
            <div className="text-center p-4 bg-yellow-100 text-yellow-800 rounded-lg shadow-md mb-8">
            {feedbackMessage}
            {loading && <LoadingSpinner size="md" color="blue" />}
            </div>
        )}

        {/* Bloco: Detalhes do Arquivo Selecionado e Botões de Ação */}
        {!feedbackMessage && selectedFileDetails && (
            <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-col md:flex-row justify-between items-start md:items-center">
            <div className="mb-4 md:mb-0 md:mr-4 flex-grow">
            <h2 className="text-xl font-semibold text-gray-800 mb-2">Detalhes do Arquivo de Dados:</h2>
            <p className="text-gray-700 text-sm mb-1"><span className="font-medium">Nome:</span> {selectedFileDetails.filename}</p>
            <p className="text-gray-700 text-sm mb-1"><span className="font-medium">Uploader:</span> {selectedFileDetails.uploader_username}</p>
            <p className="text-gray-700 text-sm mb-1"><span className="font-medium">Upload em:</span> {new Date(selectedFileDetails.uploaded_at).toLocaleDateString()}</p>
            {selectedFileDetails.description && (
                <p className="text-gray-700 text-sm mt-2"><span className="font-medium">Descrição:</span> {selectedFileDetails.description}</p>
            )}
            </div>
            <div className="flex flex-col space-y-2 md:flex-row md:space-x-2 md:space-y-0">
            {selectedFileDetails.file && (
                <a
                href={selectedFileDetails.file}
                download={selectedFileDetails.filename}
                className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded inline-flex items-center flex-shrink-0"
                title={`Baixar ${selectedFileDetails.filename}`}
                >
                <FiDownload className="mr-2" /> Baixar CSV
                </a>
            )}
            {allData.length > 0 && (
                <ExportPdfButton
                contentRef={contentToPrintRef}
                filename={`${selectedFileDetails.filename.replace(/\.csv$/, '')}_Relatorio_Indicadores.pdf`}
                title={`Relatório de Indicadores - ${selectedFileDetails.filename}`}
                />
            )}
            </div>
            </div>
        )}


        {/* Renderiza o conteúdo principal apenas se não houver feedback de error/carregamento global */}
        {!feedbackMessage && (
            <div ref={contentToPrintRef} className="grid grid-cols-1 gap-6 mt-6 p-4 bg-white rounded-lg shadow-md">
            {/* Botões de Aba */}
            <TabButtonsIndicadores
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            tabs={[
                { id: 'visao-geral', label: '🗺️ Visão Geral' },
                { id: 'analise-estado', label: '📊 Análise por Estado' },
                { id: 'analise-municipio', label: '📍 Análise por Município' },
            ]}
            />

            {/* Conteúdo da Aba Ativa */}
            <div className="min-h-[500px]">
            {activeTab === 'visao-geral' && (
                <VisaoGeralTabContent
                allData={allData}
                geojson={geojson}
                selectedIndicator={selectedIndicator}
                selectedYear={selectedYear}
                scatterX={scatterX}
                scatterY={scatterY}
                // ⭐ PASSANDO SETTERS PARA VisaoGeralTabContent ⭐
                setScatterX={setScatterX}
                setScatterY={setScatterY}
                // ⭐ FIM PASSANDO SETTERS ⭐
                loadingMap={loadingMap}
                availableIndicators={availableIndicators}
                />
            )}

            {activeTab === 'analise-estado' && (
                <AnalisePorEstadoTabContent
                allData={allData}
                selectedUf={selectedUf}
                setSelectedUf={setSelectedUf}
                selectedYear={selectedYear}
                setSelectedYear={setSelectedYear}
                selectedIndicator={selectedIndicator}
                setSelectedIndicator={setSelectedIndicator}
                rankingType={rankingType}
                setRankingType={setRankingType}
                scatterX={scatterX}
                setScatterX={setScatterX}
                scatterY={scatterY}
                setScatterY={setScatterY}
                selectedMunicipality={selectedMunicipality}
                setSelectedMunicipality={setSelectedMunicipality}
                availableUfs={availableUfs}
                availableYears={availableYears}
                availableIndicators={availableIndicators}
                ufMapConfig={ufMapConfig}
                geojson={geojson}
                loadingMap={loadingMap}
                ufDataFilteredByYear={ufDataFilteredByYear}
                ufDataAllYears={ufDataAllYears}
                mapChartData={mapChartData}
                mapTitle={mapTitle}
                />
            )}

            {activeTab === 'analise-municipio' && (
                <AnalisePorMunicipioTabContent
                allData={allData}
                selectedUf={selectedUf}
                selectedYear={selectedYear}
                selectedIndicator={selectedIndicator}
                availableUfs={availableUfs}
                availableYears={availableYears}
                availableIndicators={availableIndicators}
                ufMapConfig={ufMapConfig}
                geojson={geojson}
                loadingMap={loadingMap}
                ufDataFilteredByYear={ufDataFilteredByYear}
                ufDataAllYears={ufDataAllYears}
                selectedMunicipality={selectedMunicipality}
                setSelectedMunicipality={setSelectedMunicipality}
                mapTitle={mapTitle}
                mapChartData={mapChartData}
                />
            )}
            </div>
            </div>
        )}
        </div>
    );
};

export default IndicadoresViewerPage;
