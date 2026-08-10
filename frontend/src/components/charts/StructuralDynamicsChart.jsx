import React from 'react';
import Plot from 'react-plotly.js';

const StructuralDynamicsChart = ({ entropy, coherence }) => {
    return (
        <Plot
        data={[
            {
                x: entropy.map((_, i) => i),
            y: entropy,
            name: 'Entropia (Complexidade)',
            line: { color: '#d946ef', width: 3 }, // Magenta
            type: 'scatter'
            },
            {
                x: coherence.map((_, i) => i),
            y: coherence,
            name: 'Coerência (Estabilidade)',
            line: { color: '#06b6d4', width: 3 }, // Cyan
            type: 'scatter'
            }
        ]}
        layout={{
            title: 'Evolução da Estrutura do Sistema',
            autosize: true,
            margin: { t: 40, b: 40, l: 50, r: 20 },
            legend: { orientation: 'h', y: -0.2 },
            xaxis: { title: 'Passos de Relaxação' },
            yaxis: { title: 'Magnitude' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '300px' }}
        />
    );
};

export default StructuralDynamicsChart;
