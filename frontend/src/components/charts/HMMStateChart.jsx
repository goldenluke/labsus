import React from 'react';
import Plot from 'react-plotly.js';

const HMMStateChart = ({ data, states }) => {
    if (!states || !data) return null;
    return (
        <Plot
        data={[{
            x: data.map(d => d.ds),
            y: states,
            type: 'scatter',
            mode: 'lines',
            line: { shape: 'hv', color: '#6366f1', width: 2 },
            fill: 'tozeroy',
            fillcolor: 'rgba(99, 102, 241, 0.1)',
            name: 'Regime HMM'
        }]}
        layout={{
            title: { text: 'Transições de Regime (HMM)', font: { size: 14, color: '#64748b' } },
            autosize: true,
            margin: { t: 30, b: 30, l: 30, r: 10 },
            xaxis: { type: 'date', showgrid: false, tickfont: {size: 10} },
            yaxis: { tickvals: [0, 1], ticktext: ['Estável', 'Instável'], range: [-0.2, 1.2], tickfont: {size: 10} },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '180px' }}
        />
    );
};

export default HMMStateChart;
