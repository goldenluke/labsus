// src/components/charts/HistogramaChart.jsx
import React from 'react';
import Plot from 'react-plotly.js';

const HistogramaChart = ({ data, indicador, indicadorLabel }) => {
    return (
        <Plot
        data={[{
            type: 'histogram',
            x: data.map(item => item[indicador]),
        }]}
        layout={{
            title: `Distribuição de ${indicadorLabel}`,
            margin: { t: 40, b: 40, l: 40, r: 20 }
        }}
        className="w-full h-full"
        />
    );
};
export default HistogramaChart;
