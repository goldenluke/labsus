// src/pages/Dashboards/KMeansPerfisSaudePage.jsx

import React, { useState } from 'react';
import { useParams } from 'react-router-dom';

import useAnalysisData from '../../hooks/useAnalysisData';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FilterControls from '../../components/common/FilterControls';
import TabButtons from '../../components/common/TabButtons';

// Importando os novos componentes de abas
import MapaPrincipalTab from '../../components/dashboards/kmeans/MapaPrincipalTab';
import AnaliseRadarTab from '../../components/dashboards/kmeans/AnaliseRadarTab';

const KMeansPerfisSaudePage = () => {
    const { uf: ufParam } = useParams();
    const [activeTab, setActiveTab] = useState('mapa-principal');

    const {
        allData, loading, error,
        availableFiles, selectedFileId, setSelectedFileId,
        selectedFileDetails,
        selectedUf, setSelectedUf,
        selectedYear, setSelectedYear,
        availableUfs, availableYears, availableIndicators,
        ufDataFilteredByYear, ufDataAllYears,
        ufMapConfig,
    } = useAnalysisData('BR', null, 'perfil', ufParam, {
        fetchFileList: true,
        fileType: 'K_MEANS' // Especifica que queremos apenas arquivos K-Means
    });

    let feedbackMessage = null;
    if (error) feedbackMessage = <FeedbackMessage message={`Erro: ${error}`} type="error" />;
    else if (loading) feedbackMessage = <FeedbackMessage message="Carregando dados..." type="loading" />;
    else if (!selectedFileId) feedbackMessage = <FeedbackMessage message="Nenhum arquivo de K-Means encontrado. Use a pipeline para gerar um." type="info" />;
    else if (allData.length === 0) feedbackMessage = <FeedbackMessage message="O arquivo selecionado está vazio ou não contém dados válidos." type="error" />;

    // Simplificado, pois os filtros específicos estarão dentro das abas
    const filterControlsProps = {
        availableFiles, selectedFileId, setSelectedFileId,
        availableYears, selectedYear, setSelectedYear,
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
        Visualizador de Agrupamentos K-Means
        </h1>

        <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Seleção de Dados</h2>
        <FilterControls {...filterControlsProps} />
        </div>

        {feedbackMessage}

        {!feedbackMessage && (
            <div className="grid grid-cols-1 gap-8 mt-6">
            <TabButtons
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            tabs={[
                { id: 'mapa-principal', label: '🗺️ Mapa de Perfis' },
                { id: 'analise-radar', label: '📊 Análise de Perfis (Radar)' },
            ]}
            />

            <div className="bg-white p-4 rounded-lg shadow-md min-h-[600px] w-full">
            {activeTab === 'mapa-principal' && (
                <MapaPrincipalTab
                allData={allData}
                selectedUf={selectedUf}
                setSelectedUf={setSelectedUf}
                availableUfs={availableUfs}
                selectedYear={selectedYear}
                ufDataFilteredByYear={ufDataFilteredByYear}
                ufMapConfig={ufMapConfig}
                />
            )}
            {activeTab === 'analise-radar' && (
                <AnaliseRadarTab
                ufDataFilteredByYear={ufDataFilteredByYear}
                selectedYear={selectedYear}
                availableIndicators={availableIndicators}
                />
            )}
            </div>
            </div>
        )}
        </div>
    );
};

export default KMeansPerfisSaudePage;
