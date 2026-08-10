// src/components/dashboards/kmeans/AnaliseRadarTab.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../../config/indicadores';
import { INDICADOR_POLARIDADE } from '../../../config/polaridadeIndicadores';

const AnaliseRadarTab = ({ ufDataFilteredByYear, selectedYear, availableIndicators }) => {

    const radarChartData = useMemo(() => {
        if (!ufDataFilteredByYear.length || !availableIndicators.length) return null;

        const radarIndicators = availableIndicators.filter(ind => INDICADOR_POLARIDADE[ind]); // Apenas os que têm polaridade definida
        if (radarIndicators.length < 3) return null;

        const profiles = [...new Set(ufDataFilteredByYear.map(item => item.perfil).filter(Boolean))];
        const traces = [];

        profiles.forEach(profile => {
            const profileData = ufDataFilteredByYear.filter(item => item.perfil === profile);
            const r_values = [];

            radarIndicators.forEach(indicator => {
                const values = profileData.map(item => item[indicator]).filter(v => v != null);
                const average = values.reduce((a, b) => a + b, 0) / values.length;

                const allStateValues = ufDataFilteredByYear.map(item => item[indicator]).filter(v => v != null).sort((a,b) => a-b);
                const rank = allStateValues.findIndex(v => v >= average);
                const percentile = (rank / (allStateValues.length -1)) * 100;

                r_values.push(INDICADOR_POLARIDADE[indicator] === 'low' ? 100 - percentile : percentile);
            });

            traces.push({
                type: 'scatterpolar',
                r: [...r_values, r_values[0]],
                theta: [...radarIndicators.map(ind => INDICADORES_MAP[ind] || ind), radarIndicators.map(ind => INDICADORES_MAP[ind] || ind)[0]],
                        fill: 'toself',
                        name: profile
            });
        });

        return traces;
    }, [ufDataFilteredByYear, availableIndicators]);

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">Análise de Perfis (Radar)</h2>
        <p className="text-sm text-gray-600 italic mb-4">O gráfico de radar compara as características médias de cada perfil. Os valores são normalizados como percentis (0 = pior, 100 = melhor) em relação a todos os municípios do filtro atual.</p>
        <div className="h-[500px]">
        {radarChartData ? <Plot data={radarChartData} layout={{ polar: { radialaxis: { visible: true, range: [0, 100] } }, showlegend: true, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full">Dados insuficientes para gerar o perfil.</p>}
        </div>
        </div>
    );
};

export default AnaliseRadarTab;
