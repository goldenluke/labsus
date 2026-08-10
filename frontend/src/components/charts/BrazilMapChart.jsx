// src/components/charts/BrazilMapChart.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

const BrazilMapChart = ({ data, selectedIndicator }) => {

    const chartData = useMemo(() => {
        if (!data || data.length === 0 || !selectedIndicator) {
            return [];
        }

        return [{
            type: 'choropleth',
            geojson: '/geojson_uf/geojs-100-mun.json', // Carrega o mapa dos estados
            featureidkey: 'properties.sigla',
            locations: data.map(item => item.UF),
                              z: data.map(item => item[selectedIndicator]),
                              colorscale: 'Viridis',
                              colorbar: { title: 'Média', thickness: 15 },
                              hovertemplate: '<b>%{location}</b><br>Média: %{z:.2f}<extra></extra>',
        }];
    }, [data, selectedIndicator]);

    if (chartData.length === 0) {
        return <p className="text-center p-10">Selecione um ficheiro e um indicador para visualizar o mapa.</p>
    }

    return (
        <Plot
        data={chartData}
        layout={{
            title: `Média de "${selectedIndicator || ''}" por Estado`,
            geo: {
                scope: 'south america',
                center: { lat: -14, lon: -55 },
                projection: { scale: 3.5 },
                showland: true,
                landcolor: 'rgb(217, 217, 217)',
            subunitcolor: 'rgb(255, 255, 255)',
            },
            margin: { t: 40, b: 0, l: 0, r: 0 },
        }}
        className="w-full h-full"
        useResizeHandler
        />
    );
};

export default BrazilMapChart;
