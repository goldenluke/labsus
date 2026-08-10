// src/components/dashboards/kmeans/MapaTransicaoTab.jsx

import React, { useState, useMemo, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { UF_CONFIGS } from '../../../config/ufConfigs';

const TRANSITION_COLORS = {
    'Melhorou': '#2ca02c', // Verde
    'Piorou': '#d62728',   // Vermelho
    'Estável': '#7f7f7f',   // Cinza
    'Mudou': '#1f77b4',    // Azul para outras mudanças
    'Sem Dados': '#f0f0f0' // Cinza claro
};

const MapaTransicaoTab = ({ allData, availableUfs, availableYears }) => {
    const [startYear, setStartYear] = useState(null);
    const [endYear, setEndYear] = useState(null);
    // ⭐ ESTADO INICIAL ATUALIZADO PARA NÃO USAR 'BR' ⭐
    const [selectedUf, setSelectedUf] = useState('');
    const [geojson, setGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(false);

    const ufConfig = UF_CONFIGS[selectedUf];

    // ⭐ EFEITO PARA DEFINIR O ESTADO INICIAL QUANDO OS DADOS CHEGAREM ⭐
    useEffect(() => {
        if (availableUfs.length > 0 && !selectedUf) {
            setSelectedUf(availableUfs[0]);
        }
    }, [availableUfs, selectedUf]);

    useEffect(() => {
        if (availableYears.length > 1) {
            const sortedYears = [...availableYears].sort((a, b) => a - b);
            setStartYear(sortedYears[0]);
            setEndYear(sortedYears[sortedYears.length - 1]);
        }
    }, [availableYears]);

    useEffect(() => {
        if (!selectedUf) return;
        const fetchGeojson = async () => {
            setLoadingMap(true);
            const url = ufConfig?.ibgePrefix ? `/geojson_uf/geojs-${ufConfig.ibgePrefix}-mun.json` : null;
            if (!url) { setLoadingMap(false); return; }
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error("Arquivo GeoJSON não encontrado.");
                const data = await response.json();
                setGeojson(data);
            } catch (error) { console.error("Erro ao carregar GeoJSON:", error); }
            finally { setLoadingMap(false); }
        };
        fetchGeojson();
    }, [selectedUf, ufConfig]);

    const mapData = useMemo(() => {
        if (!geojson || !allData.length || !startYear || !endYear || startYear >= endYear) return null;

        const startData = new Map(allData.filter(d => d.ANO === startYear).map(d => [d.cod_mun_ibge_7, d.perfil]));
        const endData = new Map(allData.filter(d => d.ANO === endYear).map(d => [d.cod_mun_ibge_7, d.perfil]));

        // Filtra os municípios apenas para a UF selecionada
        const municipalitiesInUf = new Set(allData.filter(d => d.UF === selectedUf).map(d => d.cod_mun_ibge_7));

        const transitions = [];
        endData.forEach((endProfile, munCode) => {
            // Verifica se o município pertence à UF selecionada
            if (municipalitiesInUf.has(munCode)) {
                const startProfile = startData.get(munCode);
                if (startProfile && endProfile) {
                    let transitionType = 'Estável';
                    if (startProfile.includes('Vulnerabilidade') && !endProfile.includes('Vulnerabilidade')) transitionType = 'Melhorou';
                    else if (!startProfile.includes('Vulnerabilidade') && endProfile.includes('Vulnerabilidade')) transitionType = 'Piorou';
                    else if (startProfile !== endProfile) transitionType = 'Mudou';

                    transitions.push({ code: munCode, transition: transitionType, from: startProfile, to: endProfile });
                }
            }
        });

        if (transitions.length === 0) return null;

        const zMapping = Object.fromEntries(Object.keys(TRANSITION_COLORS).map((p, i) => [p, i]));

        const choroplethTrace = {
            type: 'choropleth', geojson: geojson,
            locations: transitions.map(t => String(t.code)),
                            z: transitions.map(t => zMapping[t.transition] ?? zMapping['Sem Dados']),
                            featureidkey: 'properties.id',
                            text: transitions.map(t => `${allData.find(d=>d.cod_mun_ibge_7 === t.code)?.municipio}<br>${t.from} -> ${t.to}`),
                            hoverinfo: 'text',
                            colorscale: Object.entries(TRANSITION_COLORS).map(([key, color], i) => [i / (Object.keys(TRANSITION_COLORS).length - 1), color]),
                            showscale: false,
        };

        const legendTraces = Object.entries(TRANSITION_COLORS).map(([name, color]) => ({
            x: [null], y: [null], type: 'scatter', mode: 'markers',
            marker: { color: color, size: 10 }, name: name,
            xaxis: 'x2', yaxis: 'y2'
        }));

        return [choroplethTrace, ...legendTraces];
    }, [geojson, allData, startYear, endYear, selectedUf]);

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">Mapa de Transição de Perfis</h2>
        <p className="text-sm text-gray-600 italic mb-4">
        Esta visualização mostra como os perfis de saúde dos municípios mudaram entre dois anos.
        </p>
        <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
        <label className="flex flex-col">Estado (UF):
        <select value={selectedUf} onChange={(e) => setSelectedUf(e.target.value)} className="p-2 border rounded-md">
        {/* ⭐ OPÇÃO BRASIL REMOVIDA DAQUI ⭐ */}
        {availableUfs.map(ufCode => (<option key={ufCode} value={ufCode}>{ufCode}</option>))}
        </select>
        </label>
        <label className="flex flex-col">Ano Inicial:
        <select value={startYear || ''} onChange={(e) => setStartYear(parseInt(e.target.value))} className="p-2 border rounded-md">
        {availableYears.map(y => (<option key={`start-${y}`} value={y}>{y}</option>))}
        </select>
        </label>
        <label className="flex flex-col">Ano Final:
        <select value={endYear || ''} onChange={(e) => setEndYear(parseInt(e.target.value))} className="p-2 border rounded-md">
        {availableYears.map(y => (<option key={`end-${y}`} value={y}>{y}</option>))}
        </select>
        </label>
        </div>
        <div className="h-[550px]">
        {loadingMap ? <p>Carregando mapa...</p> : (mapData ?
            <Plot
            data={mapData}
            layout={{
                geo: { scope: 'south america', fitbounds: 'locations', visible: false },
                margin: { t: 0, b: 40, l: 0, r: 0 },
                legend: { orientation: 'h', yanchor: 'bottom', y: -0.2, xanchor: 'center', x: 0.5 },
                xaxis2: { visible: false }, yaxis2: { visible: false }
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            : <p className="flex items-center justify-center h-full">Dados insuficientes para a análise de transição. Verifique se o arquivo contém dados para os dois anos selecionados.</p>)}
            </div>
            </div>
    );
};

export default MapaTransicaoTab;
