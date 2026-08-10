// src/components/charts/RankingMunicipiosChart.jsx

import React from 'react';
import Plot from 'react-plotly.js';

const RankingMunicipiosChart = ({ data, indicador, indicadorLabel, ano }) => {
    // Guarda de renderização: não faz nada se não houver dados
    if (!data || data.length === 0) {
        return <p className="p-4 text-center">Dados de ranking indisponíveis.</p>;
    }

    // Ordena os dados para mostrar os maiores valores no topo e pega os 15 melhores
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
            title: `Top 15 Municípios para ${indicadorLabel} (${ano})`,
            margin: { t: 40, b: 40, l: 150, r: 20 },
            yaxis: { autorange: 'reversed' }, // Mostra o maior valor no topo
            xaxis: { title: indicadorLabel }
        }}
        className="w-full h-full"
        useResizeHandler
        />
    );
};

export default RankingMunicipiosChart;
