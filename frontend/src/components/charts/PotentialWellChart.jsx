import React from 'react';
import Plot from 'react-plotly.js';

const PotentialWellChart = ({ centers, uValues }) => {
    return (
        <Plot
        data={[{
            x: centers,
            y: uValues,
            type: 'scatter',
            mode: 'lines',
            line: { color: '#f59e0b', width: 4, shape: 'spline' },
            fill: 'tozeroy',
            fillcolor: 'rgba(245, 158, 11, 0.1)',
            name: 'Potencial de Estabilidade'
        }]}
        layout={{
            title: 'Paisagem de Estabilidade U(x)',
            autosize: true,
            margin: { t: 40, b: 40, l: 20, r: 20 },
            xaxis: { title: 'Variação da Demanda', showgrid: false },
            yaxis: { showgrid: false, showticklabels: false },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '300px' }}
        />
    );
};

export default PotentialWellChart;
