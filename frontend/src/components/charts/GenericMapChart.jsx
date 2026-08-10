// src/components/charts/GenericMapChart.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

const GenericMapChart = ({ geojson, data, locationKey, featureIdKey, valueKey, chartKey }) => {

    const chartData = useMemo(() => {
        if (!geojson || !data || data.length === 0 || !valueKey) return null;

        const mapLocations = new Set(geojson.features.map(f => f.properties[featureIdKey]));
        const filteredData = data.filter(item => mapLocations.has(String(item[locationKey])));

        if (filteredData.length === 0) {
            console.warn("GenericMapChart: Nenhum dado correspondeu às localizações do mapa.");
            return null;
        }

        return [{
            type: 'choropleth',
            geojson: geojson,
            locations: filteredData.map(item => String(item[locationKey])),
                              z: filteredData.map(item => item[valueKey]),
                              featureidkey: `properties.${featureIdKey}`,
                              colorscale: 'Viridis',
                              colorbar: { title: 'Valor' },
        }];
    }, [geojson, data, locationKey, featureIdKey, valueKey]);

    if (!chartData) {
        return <p className="text-center p-10">Dados insuficientes para renderizar o mapa.</p>;
    }

    return (
        <Plot
        key={chartKey}
        data={chartData}
        layout={{
            geo: {
                fitbounds: "locations",
                visible: false,
            },
            // Garante que o gráfico use o espaço disponível
            autosize: true,
            margin: { t: 0, b: 0, l: 0, r: 0 },
        }}
        // ✅ ESTA É A MUDANÇA MAIS IMPORTANTE
        // Ativa o redimensionamento automático
        useResizeHandler={true}
        // As classes garantem que o elemento do Plotly tente ocupar o espaço
        className="w-full h-full"
        />
    );
};

export default GenericMapChart;
