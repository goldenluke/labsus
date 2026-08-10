// src/components/dashboards/kmeans/PerfilDetalhadoTab.jsx

import React, { useState, useMemo, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../../config/indicadores';

const PerfilDetalhadoTab = ({ ufDataFilteredByYear, availableIndicators }) => {
    const [comparisonIndicator, setComparisonIndicator] = useState('');

    useEffect(() => {
        if (availableIndicators.length > 0 && !comparisonIndicator) {
            setComparisonIndicator(availableIndicators[0]);
        }
    }, [availableIndicators, comparisonIndicator]);

    const boxPlotData = useMemo(() => {
        if (!ufDataFilteredByYear.length || !comparisonIndicator) return null;

        const profiles = [...new Set(ufDataFilteredByYear.map(item => item.perfil).filter(Boolean))].sort();
        if (profiles.length === 0) return null;

        const traces = profiles.map(profile => {
            const profileValues = ufDataFilteredByYear
            .filter(item => item.perfil === profile && item[comparisonIndicator] != null)
            .map(item => item[comparisonIndicator]);

            return {
                y: profileValues,
                type: 'box',
                name: profile,
                boxpoints: 'all' // Mostra todos os pontos
            };
        });

        return traces;
    }, [ufDataFilteredByYear, comparisonIndicator]);

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">Análise Detalhada de Perfis por Indicador</h2>
        <p className="text-sm text-gray-600 italic mb-4">
        Selecione um indicador para comparar sua distribuição (mediana, quartis e outliers) entre os diferentes perfis de saúde encontrados. Isso ajuda a validar e entender o que cada perfil representa.
        </p>

        <div className="mb-4">
        <label className="flex flex-col font-semibold">
        Selecione um Indicador para Comparar:
        <select value={comparisonIndicator} onChange={e => setComparisonIndicator(e.target.value)} className="p-2 border rounded-md mt-1 font-normal">
        {availableIndicators.map(ind => <option key={ind} value={ind}>{INDICADORES_MAP[ind] || ind}</option>)}
        </select>
        </label>
        </div>

        <div className="h-[500px]">
        {boxPlotData ? (
            <Plot
            data={boxPlotData}
            layout={{
                yaxis: { title: INDICADORES_MAP[comparisonIndicator] || comparisonIndicator },
                showlegend: false
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
        ) : <p className="flex items-center justify-center h-full">Dados insuficientes para a análise.</p>}
        </div>
        </div>
    );
};

export default PerfilDetalhadoTab;
