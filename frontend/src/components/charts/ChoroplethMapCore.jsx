// src/components/charts/ChoroplethMapCore.jsx (Crie este arquivo)

import React from 'react';
import Plot from 'react-plotly.js'; // Importa Plot aqui

const ChoroplethMapCore = ({ plotData, mapLayoutGeo, mapTitle }) => {
    if (!plotData || plotData.length === 0) {
        return <p className="text-gray-600 text-center mt-4">Sem dados para exibir no mapa.</p>;
    }

    return (
        <Plot
        data={plotData}
        layout={{
            title: {
                text: mapTitle,
                font: { size: 20, color: '#333' },
                xref: 'paper', x: 0.05, xanchor: 'left', yanchor: 'top',
            },
            geo: mapLayoutGeo,
            margin: { t: 50, b: 20, l: 20, r: 20 }, autosize: true,
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full h-full"
        />
    );
};

export default ChoroplethMapCore;
