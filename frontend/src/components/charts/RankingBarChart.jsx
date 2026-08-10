// src/components/charts/RankingBarChart.jsx

import React from 'react';
import Plot from 'react-plotly.js';

const RankingBarChart = ({ data, indicador, indicadorLabel, ano }) => {
    if (!data || data.length === 0) {
        return <p>Dados de ranking indisponíveis.</p>;
    }

    // Ordena os dados para mostrar os maiores valores no topo
    const rankedData = [...data].sort((a, b) => b[indicador] - a[indicador]);

    return (
        <Plot
        data={[{
            type: 'bar',
            y: rankedData.map(item => item.UF),
            x: rankedData.map(item => item[indicador]),
            orientation: 'h'
        }]}
        layout={{
            title: `Ranking de Estados por ${indicadorLabel} (${ano})`,
            margin: { t: 40, b: 40, l: 50, r: 20 },
            yaxis: { autorange: 'reversed' },
            xaxis: { title: indicadorLabel }
        }}
        className="w-full h-full"
        useResizeHandler
        />
    );
};

export default RankingBarChart;
