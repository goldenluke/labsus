// src/components/dashboards/kmeans/AnaliseRegionalTab.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { UF_TO_REGION_MAP } from '../../../config/regioes';

const AnaliseRegionalTab = ({ allData, selectedYear }) => {

    const regionalChartData = useMemo(() => {
        if (!allData.length || !selectedYear) return null;

        const dataForYear = allData.filter(item => item.ANO === selectedYear && item.perfil && UF_TO_REGION_MAP[item.UF]);
        if (dataForYear.length === 0) return null;

        const allProfiles = [...new Set(dataForYear.map(item => item.perfil))].sort();
        const regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'];

        const traces = allProfiles.map(profile => {
            const yValues = regions.map(region => {
                return dataForYear.filter(item => UF_TO_REGION_MAP[item.UF] === region && item.perfil === profile).length;
            });

            const firstItemWithColor = allData.find(item => item.perfil === profile && item.cor);
            const color = firstItemWithColor ? firstItemWithColor.cor : '#cccccc';

        return {
            x: regions,
            y: yValues,
            name: profile,
            type: 'bar',
            marker: { color: color }
        };
        });

        return traces;
    }, [allData, selectedYear]);

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">Distribuição de Perfis por Região do Brasil</h2>
        <p className="text-sm text-gray-600 italic mb-4">
        Este gráfico de barras empilhadas mostra a contagem de municípios para cada perfil de saúde dentro das cinco grandes regiões do país, permitindo uma análise de disparidades regionais.
        </p>
        <div className="h-[500px]">
        {regionalChartData ? (
            <Plot
            data={regionalChartData}
            layout={{
                barmode: 'stack',
                xaxis: { title: 'Região' },
                yaxis: { title: 'Número de Municípios' },
                autosize: true,
                legend: { orientation: 'h', yanchor: 'bottom', y: -0.3 }
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
        ) : <p className="flex items-center justify-center h-full">Dados insuficientes para a análise regional.</p>}
        </div>
        </div>
    );
};

export default AnaliseRegionalTab;
