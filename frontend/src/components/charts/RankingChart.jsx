// src/components/charts/RankingChart.jsx
import React from 'react';
import Plot from 'react-plotly.js';

const RankingChart = ({ data, indicador, indicadorLabel }) => {
    // Lógica de ranking (movida do seu 'components.py')
    const rankedData = [...data].sort((a, b) => b[indicador] - a[indicador]).slice(0, 15);

    return (
        <Plot
        data={[{
            type: 'bar',
            y: rankedData.map(item => item.municipio),
            x: rankedData.map(item => item[indicador]),
            orientation: 'h'
        }]}
        layout={{
            title: `Top 15 Municípios para ${indicadorLabel}`,
            margin: { t: 40, b: 40, l: 150, r: 20 },
            yaxis: { autorange: 'reversed' }
        }}
        className="w-full h-full"
        />
    );
};
export default RankingChart;
