// src/components/charts/HistoricoLineChart.jsx

import React from 'react';
import Plot from 'react-plotly.js';

const HistoricoLineChart = ({ data, indicador, indicadorLabel }) => {
    if (!data || data.length === 0) {
        return <p>Dados históricos indisponíveis.</p>;
    }

    return (
        <Plot
        data={[{
            type: 'scatter',
            mode: 'lines+markers',
            x: data.map(item => item.ANO),
            y: data.map(item => item.media_nacional),
        }]}
        layout={{
            title: `Média Histórica Nacional de ${indicadorLabel}`,
            margin: { t: 40, b: 40, l: 50, r: 20 },
            xaxis: { title: 'Ano' },
            yaxis: { title: 'Média Nacional' }
        }}
        className="w-full h-full"
        useResizeHandler
        />
    );
};

export default HistoricoLineChart;
