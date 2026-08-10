// src/components/charts/MunicipioMapChart.jsx

import React, { useMemo, useState, useEffect } from 'react';
import Plot from 'react-plotly.js';

const GEOJSON_PATHS = { 'AC': 'geojs-12-mun', 'AL': 'geojs-27-mun', 'AP': 'geojs-16-mun', 'AM': 'geojs-13-mun', 'BA': 'geojs-29-mun', 'CE': 'geojs-23-mun', 'DF': 'geojs-53-mun', 'ES': 'geojs-32-mun', 'GO': 'geojs-52-mun', 'MA': 'geojs-21-mun', 'MT': 'geojs-51-mun', 'MS': 'geojs-50-mun', 'MG': 'geojs-31-mun', 'PA': 'geojs-15-mun', 'PB': 'geojs-25-mun', 'PR': 'geojs-41-mun', 'PE': 'geojs-26-mun', 'PI': 'geojs-22-mun', 'RJ': 'geojs-33-mun', 'RN': 'geojs-24-mun', 'RS': 'geojs-43-mun', 'RO': 'geojs-11-mun', 'RR': 'geojs-14-mun', 'SC': 'geojs-42-mun', 'SP': 'geojs-35-mun', 'SE': 'geojs-28-mun', 'TO': 'geojs-17-mun', 'BR': 'geojs-100-mun' };
const GEOJSON_ID_KEY = 'id';

const MunicipioMapChart = ({ uf, data, selectedIndicator, ufConfig }) => {
    const [geojson, setGeojson] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!uf) return;
        const fetchGeojson = async () => {
            setLoading(true);
            const fileName = GEOJSON_PATHS[uf.toUpperCase()];
            if (!fileName) { setLoading(false); return; }
            const cacheBuster = `?v=${new Date().getTime()}`;
            const fileUrl = `/geojson_uf/${fileName}.json${cacheBuster}`;
            try {
                const response = await fetch(fileUrl);
                if (!response.ok) throw new Error(`Erro de rede`);
                const jsonData = await response.json();
                setGeojson(jsonData);
            } catch (error) { setGeojson(null); } finally { setLoading(false); }
        };
        fetchGeojson();
    }, [uf]);

    const chartData = useMemo(() => {
        if (!geojson || !data || data.length === 0 || !selectedIndicator) return null;

        const mapLocations = new Set(geojson.features.map(f => f.properties[GEOJSON_ID_KEY]));
        const filteredData = data.filter(item => mapLocations.has(String(item.cod_mun_ibge_7)));

        if (filteredData.length === 0) {
            // ✅ "SUPER DEBUG" LOG
            if (geojson.features.length > 0 && data.length > 0) {
                console.groupCollapsed("%c--- DEBUG DE LIGAÇÃO DE DADOS (FALHOU) ---", "color: orange; font-weight: bold;");
                const firstMapId = geojson.features[0].properties[GEOJSON_ID_KEY];
                const firstDataId = data[0].cod_mun_ibge_7;
                console.log(`Primeiro ID do Mapa (GeoJSON): '${firstMapId}' (comprimento: ${firstMapId.length})`);
                console.log(`Primeiro ID dos Seus Dados (CSV): '${firstDataId}' (comprimento: ${String(firstDataId).length})`);
                console.error("CONCLUSÃO: Os IDs não correspondem. Verifique se ambos têm 7 dígitos.");
                console.groupEnd();
            }
            return null;
        }

        return [{
            type: 'choropleth',
            geojson: geojson,
            locations: filteredData.map(item => String(item.cod_mun_ibge_7)),
                              z: filteredData.map(item => item[selectedIndicator]),
                              featureidkey: `properties.${GEOJSON_ID_KEY}`,
                              colorscale: 'Viridis',
                              colorbar: { title: 'Valor' },
        }];
    }, [data, selectedIndicator, geojson, uf]);

    if (!ufConfig) return <p>Aguardando configuração do mapa...</p>;
    if (loading) return <p>Carregando mapa...</p>;
    if (!geojson) return <p>Não foi possível carregar o mapa para {uf}.</p>;
    if (!chartData) return <p>Mapa carregado, mas sem dados correspondentes para exibir. Verifique o console para detalhes.</p>;

    return (
        <Plot
        key={uf}
        data={chartData}
        layout={{
            geo: {
                fitbounds: "locations",
                visible: false,
            },
            margin: { t: 0, b: 0, l: 0, r: 0 },
        }}
        className="w-full h-full"
        />
    );
};

export default MunicipioMapChart;
