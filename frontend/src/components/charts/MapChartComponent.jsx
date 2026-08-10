// src/components/charts/MapaCoropleticoEstado.jsx

import React, { useMemo, useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import axios from 'axios'; // ⭐ NOVO: Importar axios ⭐
import { UF_CONFIGS } from '../../config/ufConfigs';
import { INDICADORES_MAP } from '../../config/indicadores';

const GEOJSON_ID_KEY = 'id';

const DEFAULT_PROFILE_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
'#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
];


const MapaCoropleticoEstado = ({ uf, data, selectedIndicator, ufConfig, selectedYear }) => {
    const [geojson, setGeojson] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Efeito para buscar os dados GeoJSON da UF selecionada na sua API Django
    useEffect(() => {
        if (!uf) return;

        const fetchGeojson = async () => {
            setLoading(true);
            setError(null);
            const apiUrl = `/api/geojson/${uf.toUpperCase()}/`;
            try {
                const token = localStorage.getItem('authToken'); // Obter o token
                // ⭐ CORREÇÃO CRÍTICA AQUI: Usar axios.get em vez de fetch ⭐
                const response = await axios.get(apiUrl, {
                    headers: { 'Authorization': `Token ${token}` }
                });
                const jsonData = response.data; // Axios já retorna data como JSON
                setGeojson(jsonData);
            } catch (err) {
                console.error("Erro ao buscar GeoJSON:", err);
                setError(`Não foi possível carregar o mapa para ${uf.toUpperCase()}. Detalhes: ${err.response?.statusText || err.message}`);
                setGeojson(null);
            } finally {
                setLoading(false);
            }
        };
        fetchGeojson();
    }, [uf]); // Dependência: executa sempre que a UF muda

    // Prepara os dados para o gráfico coroplético do Plotly
    const plotData = useMemo(() => {
        if (!geojson || !data || data.length === 0 || !selectedIndicator) {
            return null;
        }

        const dataForPlotting = data;

        const municipalityDataMap = new Map();
        dataForPlotting.forEach(item => {
            // Usar cod_mun_ibge_7 para a chave do mapa, conforme seu GeoJSON
            municipalityDataMap.set(String(item.cod_mun_ibge_7), {
                value: item[selectedIndicator],
                color: item.cor
            });
        });

        const locations = [];
        const zValues = [];
        const textValues = [];
        const markerColors = [];

        const allPossibleZValues = [...new Set(dataForPlotting.map(item => item[selectedIndicator]))]
        .filter(Boolean)
        .sort((a,b) => String(a).localeCompare(String(b)));

        const discreteColorsMap = {};
        allPossibleZValues.forEach((val, index) => {
            const sampleItem = dataForPlotting.find(item => item[selectedIndicator] === val && item.cor);
            if (sampleItem && sampleItem.cor) {
                discreteColorsMap[val] = sampleItem.cor;
            } else {
                discreteColorsMap[val] = DEFAULT_PROFILE_COLORS[index % DEFAULT_PROFILE_COLORS.length];
            }
        });


        geojson.features.forEach(feature => {
            const geoId = String(feature.properties[GEOJSON_ID_KEY]);
            const clusterInfo = municipalityDataMap.get(geoId);
            const municipioName = feature.properties.nome;
            const ufCodeFromGeoId = String(feature.properties[GEOJSON_ID_KEY]).substring(0,2);
            const ufNameInGeojson = UF_CONFIGS[Object.keys(UF_CONFIGS).find(key => UF_CONFIGS[key].ibgePrefix === ufCodeFromGeoId)]?.nome || feature.properties.UF || ufCodeFromGeoId;

            locations.push(geoId);

            if (clusterInfo && clusterInfo.value !== null && clusterInfo.value !== undefined) {
                zValues.push(clusterInfo.value);
                markerColors.push(clusterInfo.color || discreteColorsMap[clusterInfo.value]);
                textValues.push(`${municipioName} (${ufNameInGeojson})<br>${selectedIndicator}: ${clusterInfo.value}`);
            } else {
                zValues.push(null);
                markerColors.push('#cccccc');
                textValues.push(`${municipioName} (${ufNameInGeojson})<br>Sem dados.`);
            }
        });

        if (locations.length === 0) {
            return null;
        }

        return [{
            type: 'choropleth',
            geojson: geojson,
            locations: locations,
            z: zValues,
            text: textValues,
            hoverinfo: 'text',
            featureidkey: `properties.${GEOJSON_ID_KEY}`,
            marker: {
                line: { color: 'white', width: 0.5 },
                color: markerColors
            },
            showscale: false,
        }];
    }, [data, selectedIndicator, geojson, selectedYear, uf]); // selectedYear e uf adicionados para dependências


    // Constrói o título dinâmico do mapa
    const mapTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const ufName = ufConfig?.nome || uf?.toUpperCase() || 'Estado';
        return `Distribuição de ${indicatorLabel} em ${ufName} (${selectedYear})`;
    }, [selectedIndicator, ufConfig, uf, selectedYear]);

    // Define a configuração de layout geográfico do mapa (zoom, centro)
    const mapLayoutGeo = useMemo(() => {
        const baseGeoConfig = {
            scope: 'south america',
            showland: true, landcolor: 'rgb(243,243,243)',
                                 countrycolor: 'rgb(204,204,204)', projection: { type: 'mercator' },
                                 visible: false,
                                 subunitcolor: 'rgb(204,204,204)', // Cor dos sub-limites (municípios dentro de um GeoJSON de estado)
    coastlinecolor: 'rgb(204,204,204)',
        };

        if (uf === 'BR') {
            return {
                ...baseGeoConfig,
                fitbounds: false,
                center: { lat: -14, lon: -50 },
                lataxis: { range: [-35, 5] },
                lonaxis: { range: [-75, -30] },
                zoom: 2.5,
            };
        } else if (ufConfig && ufConfig.zoom && ufConfig.center) {
            return {
                ...baseGeoConfig,
                fitbounds: 'locations',
                center: ufConfig.center,
                zoom: ufConfig.zoom,
            };
        }
        return baseGeoConfig;
    }, [ufConfig, uf]);


    // Mensagens de carregamento e erro
    if (error) return <p className="text-red-500 text-center mt-4">Erro ao carregar mapa: {error}</p>;
    if (loading) return <p className="text-gray-600 text-center mt-4">Carregando mapa GeoJSON para {uf}...</p>;
    if (!geojson) return <p className="text-gray-600 text-center mt-4">Não foi possível carregar o mapa GeoJSON para {uf}.</p>;
    if (!data || data.length === 0) return <p className="text-gray-600 text-center mt-4">Sem dados para exibir no mapa.</p>;
    if (!plotData) return <p className="text-gray-600 text-center mt-4">Mapa carregado, mas sem dados correspondentes para exibir com o indicador selecionado. Verifique os filtros e IDs.</p>;

    return (
        <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
        <Plot
        data={plotData}
        layout={{
            title: {
                text: mapTitle,
                font: { size: 20, color: '#333' },
                xref: 'paper',
                x: 0.05,
                xanchor: 'left',
                yanchor: 'top',
            },
            geo: mapLayoutGeo,
            margin: { t: 50, b: 20, l: 20, r: 20 },
            autosize: true,
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full h-full"
        />
        </div>
    );
};

export default MapaCoropleticoEstado;
