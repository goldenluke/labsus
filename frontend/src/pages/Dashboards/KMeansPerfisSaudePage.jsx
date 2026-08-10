// src/pages/Dashboards/KMeansPerfisSaudePage.jsx

import React, { useState } from 'react';
import { useParams } from 'react-router-dom';

import useAnalysisData from '../../hooks/useAnalysisData';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FilterControls from '../../components/common/FilterControls';
import TabButtons from '../../components/common/TabButtons';

import MapaPrincipalTab from '../../components/dashboards/kmeans/MapaPrincipalTab';
import AnaliseRadarTab from '../../components/dashboards/kmeans/AnaliseRadarTab';
import MapaComparacaoTab from '../../components/dashboards/kmeans/MapaComparacaoTab';
import AnimacaoTab from '../../components/dashboards/kmeans/AnimacaoTab';
import AnaliseRegionalTab from '../../components/dashboards/kmeans/AnaliseRegionalTab';
import PerfilDetalhadoTab from '../../components/dashboards/kmeans/PerfilDetalhadoTab';
import MapaTransicaoTab from '../../components/dashboards/kmeans/MapaTransicaoTab'; // ⭐ 1. Importe o novo componente

const KMeansPerfisSaudePage = () => {
    const { uf: ufParam } = useParams();
    const [activeTab, setActiveTab] = useState('mapa-principal');

    const {
        allData, loading, error,
        availableFiles, selectedFileId, setSelectedFileId,
        selectedUf, setSelectedUf,
        selectedYear, setSelectedYear,
        availableUfs, availableYears, availableIndicators,
        ufDataFilteredByYear,
        ufMapConfig,
    } = useAnalysisData('BR', null, 'perfil', ufParam, {
        fetchFileList: true,
        fileType: 'K_MEANS'
    });

    let feedbackMessage = null;
    if (error) feedbackMessage = <FeedbackMessage message={`Erro: ${error}`} type="error" />;
    else if (loading) feedbackMessage = <FeedbackMessage message="Carregando dados..." type="loading" />;
    else if (!selectedFileId) feedbackMessage = <FeedbackMessage message="Nenhum arquivo de K-Means encontrado. Use a pipeline para gerar um." type="info" />;
    else if (allData.length === 0) feedbackMessage = <FeedbackMessage message="O arquivo selecionado está vazio ou não contém dados válidos." type="error" />;

    const filterControlsProps = {
        availableFiles, selectedFileId, setSelectedFileId,
        availableYears, selectedYear, setSelectedYear,
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl text-center text-gray-800 mb-8">
        Agrupamentos K-Means
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
                { id: 'mapa-comparacao', label: '⚖️ Comparar Mapas' },
                { id: 'mapa-transicao', label: '↔️ Mapa de Transição' }, // ⭐ 2. Adicione a nova aba
                { id: 'animacao', label: '🎥 Evolução Temporal' },
                { id: 'analise-radar', label: '📊 Perfil (Radar)' },
                              { id: 'perfil-detalhado', label: '🔍 Detalhes do Perfil' },
            ]}
            />

            <div className="bg-white p-4 rounded-lg shadow-md min-h-[600px] w-full">
            {activeTab === 'mapa-principal' && (
                <MapaPrincipalTab allData={allData} selectedUf={selectedUf} setSelectedUf={setSelectedUf} availableUfs={availableUfs} selectedYear={selectedYear} ufDataFilteredByYear={ufDataFilteredByYear} ufMapConfig={ufMapConfig} />
            )}
            {activeTab === 'mapa-comparacao' && (
                <MapaComparacaoTab allData={allData} availableUfs={availableUfs} availableYears={availableYears} />
            )}
            {/* ⭐ 3. Adicione a renderização do novo componente ⭐ */}
            {activeTab === 'mapa-transicao' && (
                <MapaTransicaoTab
                allData={allData}
                availableUfs={availableUfs}
                availableYears={availableYears}
                />
            )}
            {activeTab === 'animacao' && (
                <AnimacaoTab allData={allData} availableUfs={availableUfs} availableYears={availableYears} />
            )}
            {activeTab === 'analise-radar' && (
                <AnaliseRadarTab ufDataFilteredByYear={ufDataFilteredByYear} selectedYear={selectedYear} availableIndicators={availableIndicators} />
            )}
            {activeTab === 'perfil-detalhado' && (
                <PerfilDetalhadoTab
                ufDataFilteredByYear={ufDataFilteredByYear}
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
