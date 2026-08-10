// src/components/dashboards/kmeans/MapaComparacaoTab.jsx

import React, { useState, useMemo, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { UF_CONFIGS } from '../../../config/ufConfigs';

const MapCard = ({ allData, availableUfs, availableYears, uf, setUf, year, setYear }) => {
    const [geojson, setGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(false);
    const ufConfig = UF_CONFIGS[uf];

    useEffect(() => {
        if (!uf) return;
        const fetchGeojson = async () => {
            setLoadingMap(true);
            const url = ufConfig?.ibgePrefix ? `/geojson_uf/geojs-${ufConfig.ibgePrefix}-mun.json` : null;
            if (!url) {
                setLoadingMap(false);
                return;
            }
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error("Arquivo GeoJSON não encontrado.");
                const data = await response.json();
                setGeojson(data);
            } catch (error) {
                setGeojson(null);
            } finally {
                setLoadingMap(false);
            }
        };
        fetchGeojson();
    }, [uf, ufConfig]);

    const mapData = useMemo(() => {
        if (!geojson || !allData.length || !year) return null;
        let dataToPlot = allData.filter(item => item.ANO === year && item.UF === uf);
        if (dataToPlot.length === 0) return null;

        const uniqueProfiles = [...new Set(dataToPlot.map(item => item.perfil).filter(Boolean))].sort();
        const colorsMap = new Map();
        uniqueProfiles.forEach(profile => {
            const itemWithColor = dataToPlot.find(item => item.perfil === profile && item.cor);
            colorsMap.set(profile, itemWithColor ? itemWithColor.cor : '#cccccc');
        });
        const zMapping = Object.fromEntries(uniqueProfiles.map((p, i) => [p, i]));

        const choroplethTrace = {
            type: 'choropleth', geojson: geojson,
            locations: dataToPlot.map(d => String(d.cod_mun_ibge_7)),
                            z: dataToPlot.map(d => zMapping[d.perfil]),
                            featureidkey: 'properties.id',
                            text: dataToPlot.map(d => d.nome_mun || d.municipio),
                            hoverinfo: 'text', customdata: dataToPlot.map(d => d.perfil),
                            hovertemplate: '<b>%{text}</b><br>Perfil: %{customdata}<extra></extra>',
                            colorscale: uniqueProfiles.map((p, i) => [i / (uniqueProfiles.length - 1 || 1), colorsMap.get(p)]),
                            showscale: false,
                            showlegend: false,
        };
        const legendTraces = [];
        colorsMap.forEach((color, profileName) => {
            legendTraces.push({
                x: [null], y: [null], type: 'scatter', mode: 'markers',
                marker: { color: color, size: 10 },
                name: profileName,
                xaxis: 'x2',
                yaxis: 'y2'
            });
        });
        return [choroplethTrace, ...legendTraces];
    }, [geojson, allData, year, uf]);

    return (
        <div className="flex flex-col border rounded-lg p-2">
        <div className="flex flex-col sm:flex-row gap-2 mb-2">
        <select value={uf || ''} onChange={(e) => setUf(e.target.value)} className="p-2 border rounded-md w-full sm:w-1/2">
        {/* ⭐ OPÇÃO BRASIL REMOVIDA DAQUI ⭐ */}
        {availableUfs.map(ufCode => (<option key={ufCode} value={ufCode}>{ufCode}</option>))}
        </select>
        <select value={year || ''} onChange={(e) => setYear(parseInt(e.target.value))} className="p-2 border rounded-md w-full sm:w-1/2">
        {availableYears.map(y => (<option key={y} value={y}>{y}</option>))}
        </select>
        </div>
        <div className="flex-grow h-[550px]">
        {loadingMap ? <p>Carregando mapa...</p> : (mapData ?
            <Plot
            data={mapData}
            layout={{
                geo: { scope: 'south america', fitbounds: 'locations', visible: false },
                margin: { t: 0, b: 40, l: 0, r: 0 },
                legend: { orientation: 'h', yanchor: 'bottom', y: -0.2, xanchor: 'center', x: 0.5 },
                xaxis2: { visible: false, range: [0, 1] },
                yaxis2: { visible: false, range: [0, 1] }
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            : <p className="flex items-center justify-center h-full">Sem dados para exibir.</p>)}
            </div>
            </div>
    );
};

const MapaComparacaoTab = ({ allData, availableUfs, availableYears }) => {
    // ⭐ ESTADO INICIAL ATUALIZADO PARA NÃO USAR 'BR' ⭐
    const [ufLeft, setUfLeft] = useState('');
    const [yearLeft, setYearLeft] = useState(null);
    const [ufRight, setUfRight] = useState('');
    const [yearRight, setYearRight] = useState(null);

    // Efeito para definir os valores iniciais quando os dados estiverem disponíveis
    useEffect(() => {
        if (availableUfs.length > 0) {
            setUfLeft(availableUfs[0]);
            // Define o mapa da direita para o segundo estado, se existir, senão usa o primeiro
            setUfRight(availableUfs.length > 1 ? availableUfs[1] : availableUfs[0]);
        }
        if (availableYears.length > 0) {
            setYearLeft(availableYears[0]);
            setYearRight(availableYears.length > 1 ? availableYears[1] : availableYears[0]);
        }
    }, [availableUfs, availableYears]);

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Comparar Mapas de Perfis</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MapCard
        allData={allData}
        availableUfs={availableUfs}
        availableYears={availableYears}
        uf={ufLeft} setUf={setUfLeft}
        year={yearLeft} setYear={setYearLeft}
        />
        <MapCard
        allData={allData}
        availableUfs={availableUfs}
        availableYears={availableYears}
        uf={ufRight} setUf={setUfRight}
        year={yearRight} setYear={setYearRight}
        />
        </div>
        </div>
    );
};

export default MapaComparacaoTab;
