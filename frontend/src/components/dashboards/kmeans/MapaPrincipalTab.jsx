// src/components/dashboards/kmeans/MapaPrincipalTab.jsx

import React, { useState, useMemo, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { UF_CONFIGS } from '../../../config/ufConfigs';

const MapaPrincipalTab = ({ allData, selectedUf, setSelectedUf, availableUfs, selectedYear, ufDataFilteredByYear, ufMapConfig }) => {
    const [geojson, setGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(false);
    const [availableProfiles, setAvailableProfiles] = useState([]);
    const [selectedProfile, setSelectedProfile] = useState('Todos');

    useEffect(() => {
        if (allData.length > 0) {
            const profiles = [...new Set(allData.map(item => item.perfil).filter(Boolean))].sort();
            setAvailableProfiles(profiles);
        }
    }, [allData]);

    useEffect(() => {
        if (!selectedUf || selectedUf === 'BR') return; // Não carrega mapa se for BR
        const fetchGeojson = async () => {
            setLoadingMap(true);
            const url = ufMapConfig?.ibgePrefix ? `/geojson_uf/geojs-${ufMapConfig.ibgePrefix}-mun.json` : null;
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
                console.error("Erro ao carregar GeoJSON:", error);
            } finally {
                setLoadingMap(false);
            }
        };
        fetchGeojson();
    }, [selectedUf, ufMapConfig]);

    const mapData = useMemo(() => {
        if (!geojson || !ufDataFilteredByYear.length) return null;
        let dataToPlot = ufDataFilteredByYear;
        if (selectedProfile !== 'Todos') {
            dataToPlot = dataToPlot.filter(item => item.perfil === selectedProfile);
        }
        if(dataToPlot.length === 0) return null;

        const uniqueProfiles = [...new Set(dataToPlot.map(item => item.perfil).filter(Boolean))].sort();
        const colorsMap = new Map();
        uniqueProfiles.forEach(profile => {
            const itemWithColor = dataToPlot.find(item => item.perfil === profile && item.cor);
            colorsMap.set(profile, itemWithColor ? itemWithColor.cor : '#cccccc');
        });
        const zMapping = Object.fromEntries(uniqueProfiles.map((p, i) => [p, i]));

        const choroplethTrace = {
            type: 'choropleth',
            geojson: geojson,
            locations: dataToPlot.map(d => String(d.cod_mun_ibge_7)),
                            z: dataToPlot.map(d => zMapping[d.perfil]),
                            featureidkey: 'properties.id',
                            text: dataToPlot.map(d => d.nome_mun || d.municipio),
                            hoverinfo: 'text',
                            customdata: dataToPlot.map(d => d.perfil),
                            hovertemplate: '<b>%{text}</b><br>Perfil: %{customdata}<extra></extra>',
                            // Com um único perfil, i / (length - 1) vira i / 0 (ou o fallback
                            // `|| 1` mascara isso só para length===1, gerando UM stop em vez
                            // de dois) — Plotly não consegue interpolar/pintar um colorscale
                            // de um stop só e cai para cinza. Repete a mesma cor em [0, 1]
                            // nesse caso para o mapa ficar sólido na cor certa.
                            colorscale: uniqueProfiles.length === 1
                                ? [[0, colorsMap.get(uniqueProfiles[0])], [1, colorsMap.get(uniqueProfiles[0])]]
                                : uniqueProfiles.map((p, i) => [i / (uniqueProfiles.length - 1), colorsMap.get(p)]),
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
    }, [geojson, ufDataFilteredByYear, selectedProfile]);

    if (loadingMap) return <div className="flex items-center justify-center h-full">Carregando mapa...</div>;

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Mapa de Perfis de Saúde</h2>
        <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
        <label className="flex flex-col">Estado (UF):
        <select value={selectedUf} onChange={(e) => setSelectedUf(e.target.value)} className="p-2 border rounded-md">
        {/* ⭐ OPÇÃO BRASIL REMOVIDA DAQUI ⭐ */}
        {availableUfs.map(ufCode => (<option key={ufCode} value={ufCode}>{ufCode}</option>))}
        </select>
        </label>
        <label className="flex flex-col">Filtrar por Perfil:
        <select value={selectedProfile} onChange={(e) => setSelectedProfile(e.target.value)} className="p-2 border rounded-md">
        <option value="Todos">Todos os Perfis</option>
        {availableProfiles.map(p => (<option key={p} value={p}>{p}</option>))}
        </select>
        </label>
        </div>
        <div className="h-[550px]">
        {mapData ?
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
            : <p className="flex items-center justify-center h-full">Nenhum dado para exibir no mapa com os filtros atuais.</p>}
            </div>
            </div>
    );
};

export default MapaPrincipalTab;
